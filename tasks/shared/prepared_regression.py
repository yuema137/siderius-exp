"""Task-owned array adapter for frozen, scalar-regression prepared views.

No preprocessing runs here. Scopes contain row identities, never target values.
Validation materialization and scoring require evaluator filesystem access;
this adapter is not itself a process-isolation boundary.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, ClassVar, Literal

import numpy as np
import torch
from execute_tools.evaluation_metric import (
    ScoreabilityContract,
    ScoreabilityFailure,
    ScoreabilityVerdict,
)
from execute_tools.task_data_path import (
    DeliverableWriteRequest,
    EpochSamplingParams,
    EvalMaterializationParams,
    EvaluationReadRequest,
    HealthCoverageRequest,
    HealthCoverageResult,
    ScopeBuildRequest,
    StorageReadScope,
    TaskOutputArtifactInventory,
    ValidationScopeError,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    model_validator,
)
from torch.utils.data import Dataset


class PreparedDeclaration(BaseModel):
    """Public identity of the prepared arrays; no validation statistics."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    task_id: str
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    train_count: int = Field(gt=0)
    validation_count: int = Field(gt=0)
    channels: int = Field(gt=0)
    length: int = Field(gt=0)
    loss_indices: tuple[StrictInt, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def check_loss_population(self) -> PreparedDeclaration:
        if tuple(sorted(set(self.loss_indices))) != self.loss_indices:
            raise ValueError("loss indices must be unique and ascending")
        if self.loss_indices[0] < 0 or self.loss_indices[-1] >= self.validation_count:
            raise ValueError("loss index outside validation population")
        if len(self.loss_indices) * 10 != self.validation_count:
            raise ValueError("loss indices must cover exactly 10% of validation")
        return self


class PreparedScope(BaseModel):
    """A compact full population or an explicit, ordered subset."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    declaration_sha256: str
    split: Literal["train", "validation"]
    population_count: int = Field(gt=0)
    selected_rows: tuple[StrictInt, ...] | None = None

    @model_validator(mode="after")
    def check_rows(self) -> PreparedScope:
        rows = self.selected_rows
        if rows is not None:
            if not rows or tuple(sorted(set(rows))) != rows:
                raise ValueError("selected rows must be nonempty, unique and ascending")
            if rows[0] < 0 or rows[-1] >= self.population_count:
                raise ValueError("selected row outside split population")
        return self

    @property
    def row_count(self) -> int:
        return (
            self.population_count
            if self.selected_rows is None
            else len(self.selected_rows)
        )

    @property
    def rows(self) -> tuple[int, ...] | range:
        return (
            range(self.population_count)
            if self.selected_rows is None
            else self.selected_rows
        )

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(f"{self.split}:{row}" for row in self.rows)

    def truth(self, data_dir: str) -> np.ndarray:
        """Called by trusted scoring; targets are not part of scope transport."""
        targets = np.load(
            _split_dir(data_dir, self.split) / "targets.npy",
            mmap_mode="r",
            allow_pickle=False,
        )
        if targets.dtype != np.float32 or targets.shape != (self.population_count, 1):
            raise ValidationScopeError("prepared target dtype or population changed")
        return np.asarray(targets[list(self.rows), 0], dtype=np.float64)


def _split_dir(data_dir: str, split: str) -> Path:
    return Path(data_dir) / ("training" if split == "train" else "evaluator/validation")


class PreparedDataset(Dataset[Any]):
    """Read-only memory maps, opened once per dataset, with owned tensor rows."""

    def __init__(self, scope: PreparedScope, data_dir: str, channels: int, length: int):
        self.scope = scope
        root = _split_dir(data_dir, scope.split)
        self.inputs = np.load(root / "inputs.npy", mmap_mode="r", allow_pickle=False)
        self.targets = np.load(root / "targets.npy", mmap_mode="r", allow_pickle=False)
        if self.inputs.dtype != np.float32 or self.inputs.shape != (
            scope.population_count,
            channels,
            length,
        ):
            raise ValidationScopeError("prepared input shape or dtype changed")
        if self.targets.dtype != np.float32 or self.targets.shape != (
            scope.population_count,
            1,
        ):
            raise ValidationScopeError("prepared target shape or dtype changed")

    def __len__(self) -> int:
        return self.scope.row_count

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.scope.rows[index]
        return torch.from_numpy(self.inputs[row].copy()), torch.from_numpy(
            self.targets[row].copy()
        )


class PredictionArtifact(BaseModel):
    """One scalar in physical units per declared validation row."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    format: Literal["prepared_scalar_predictions_v1"] = "prepared_scalar_predictions_v1"
    declaration_sha256: str
    split: Literal["validation"]
    predictions: dict[str, StrictFloat] = Field(min_length=1)

    @model_validator(mode="after")
    def finite_predictions(self) -> PredictionArtifact:
        if not all(math.isfinite(value) for value in self.predictions.values()):
            raise ValueError("predictions must be finite real numbers")
        return self


def _unique_json(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_predictions(path: Path) -> PredictionArtifact:
    return PredictionArtifact.model_validate(
        json.loads(path.read_text(), object_pairs_hook=_unique_json)
    )


def deliverable_name(request: DeliverableWriteRequest | EvaluationReadRequest) -> str:
    return f"predictions_{request.model_type}_{request.run_name}_{request.exp_id}.json"


class PreparedRegressionDataPath:
    """Common mechanics; each task binds a public declaration by file reference."""

    task_data_path_id: ClassVar[str]

    def __init__(self, declaration_path: str):
        raw = Path(declaration_path).read_bytes()
        self.declaration = PreparedDeclaration.model_validate_json(raw)
        self.declaration_sha256 = hashlib.sha256(raw).hexdigest()
        if self.declaration.task_id != self.task_data_path_id:
            raise ValueError("prepared declaration belongs to another task")
        self._verified_manifests: set[tuple[str, int, int]] = set()

    def _scope(self, scope: object) -> PreparedScope:
        if not isinstance(scope, PreparedScope):
            raise TypeError("expected a prepared regression scope")
        expected = (
            self.declaration.train_count
            if scope.split == "train"
            else self.declaration.validation_count
        )
        if (
            scope.declaration_sha256 != self.declaration_sha256
            or scope.population_count != expected
        ):
            raise ValueError("scope does not belong to this prepared declaration")
        return scope

    def _build(
        self, request: ScopeBuildRequest, split: Literal["train", "validation"]
    ) -> PreparedScope:
        if request.subset_ref is not None or any(
            p != 0 for p in request.target_partitions
        ):
            raise ValueError(
                "one array partition per split; use portion to select rows"
            )
        count = (
            self.declaration.train_count
            if split == "train"
            else self.declaration.validation_count
        )
        keep = max(1, math.ceil(count * request.portion))
        if request.max_samples is not None:
            keep = min(keep, request.max_samples)
        rows = None
        if keep < count:
            if split == "train":
                selected = np.random.default_rng(request.seed or 0).choice(
                    count, keep, replace=False
                )
            else:
                # All validation scopes are stable across planner seeds. The
                # exact frozen loss subset is the first 10% of this ordering.
                frozen = np.array(self.declaration.loss_indices, dtype=np.int64)
                rng = np.random.default_rng(0)
                if keep <= len(frozen):
                    selected = rng.permutation(frozen)[:keep]
                else:
                    remaining = np.setdiff1d(
                        np.arange(count), frozen, assume_unique=True
                    )
                    selected = np.concatenate(
                        (frozen, rng.permutation(remaining)[: keep - len(frozen)])
                    )
            rows = tuple(int(row) for row in np.sort(selected))
        return PreparedScope(
            declaration_sha256=self.declaration_sha256,
            split=split,
            population_count=count,
            selected_rows=rows,
        )

    def build_training_scope(self, request: ScopeBuildRequest) -> object:
        return self._build(request, "train")

    def build_eval_scope(self, request: ScopeBuildRequest) -> object:
        return self._build(request, "validation")

    def serialize_scope(self, scope: object) -> str:
        return self._scope(scope).model_dump_json()

    def deserialize_scope(self, payload: str) -> object:
        return self._scope(PreparedScope.model_validate_json(payload))

    def _check_manifest(self, data_dir: str) -> None:
        # Hash metadata once, not multi-GB arrays per epoch. Full array hashes
        # belong to deployment qualification; shape/dtype are checked on open.
        path = (Path(data_dir) / "manifest.json").resolve()
        info = path.stat()
        identity = (str(path), info.st_size, info.st_mtime_ns)
        if identity not in self._verified_manifests:
            if (
                hashlib.sha256(path.read_bytes()).hexdigest()
                != self.declaration.manifest_sha256
            ):
                raise ValidationScopeError(
                    "prepared manifest digest does not match the task declaration"
                )
            self._verified_manifests.add(identity)

    def training_dataset(
        self, scope: object, params: EpochSamplingParams
    ) -> Dataset[Any]:
        checked = self._scope(scope)
        if checked.split != "train":
            raise ValidationScopeError("training requires the training split")
        self._check_manifest(params.data_dir)
        keep = max(1, math.ceil(checked.row_count * (params.train_portion or 1.0)))
        if params.max_samples is not None:
            keep = min(keep, params.max_samples)
        if keep < checked.row_count:
            chosen = np.random.default_rng(params.epoch_seed).choice(
                np.asarray(checked.rows), keep, replace=False
            )
            checked = checked.model_copy(
                update={"selected_rows": tuple(int(row) for row in np.sort(chosen))}
            )
        return PreparedDataset(
            checked, params.data_dir, self.declaration.channels, self.declaration.length
        )

    def validation_dataset(
        self, scope: object, params: EvalMaterializationParams
    ) -> Dataset[Any]:
        checked = self._scope(scope)
        if checked.split != "validation":
            raise ValidationScopeError("validation requires the validation split")
        self._check_manifest(params.data_dir)
        return PreparedDataset(
            checked, params.data_dir, self.declaration.channels, self.declaration.length
        )

    def max_inference_batch_size(self) -> int:
        return 64

    def validate_health_coverage(
        self, request: HealthCoverageRequest
    ) -> HealthCoverageResult:
        return HealthCoverageResult(
            applicable=False,
            covered=False,
            reason="No task-specific Health thresholds are declared; scoreability checks finite outputs and coverage.",
        )

    def storage_read_scope(self, data_dir: str, scope: object) -> StorageReadScope:
        root = _split_dir(data_dir, self._scope(scope).split)
        paths = tuple(root / name for name in ("inputs.npy", "targets.npy"))
        return StorageReadScope(
            file_paths=tuple(str(p.resolve()) for p in paths),
            expected_on_disk_bytes=sum(p.stat().st_size for p in paths),
        )

    def write_deliverable(self, outputs: Any, request: DeliverableWriteRequest) -> None:
        scope = self._scope(request.task_scope)
        if scope.split != "validation":
            raise ValueError("deliverables require validation scopes")
        predictions = np.asarray(
            [torch.as_tensor(value).detach().cpu().numpy() for value in outputs]
        )
        if predictions.shape not in ((scope.row_count,), (scope.row_count, 1)):
            raise ValueError(f"expected one scalar per row; got {predictions.shape}")
        artifact = PredictionArtifact(
            declaration_sha256=self.declaration_sha256,
            split=scope.split,
            predictions=dict(
                zip(scope.keys, predictions.reshape(-1).tolist(), strict=True)
            ),
        )
        path = Path(request.output_dir) / deliverable_name(request)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(artifact.model_dump_json())

    def read_evaluation_payload(self, request: EvaluationReadRequest) -> object:
        artifact = read_predictions(
            Path(request.deliverable_dir) / deliverable_name(request)
        )
        if artifact.declaration_sha256 != self.declaration_sha256:
            raise ValueError("prediction declaration identity mismatch")
        return artifact.predictions

    def enumerate_output_artifacts(
        self, request: EvaluationReadRequest
    ) -> TaskOutputArtifactInventory:
        name = deliverable_name(request)
        path = Path(request.deliverable_dir) / name
        return TaskOutputArtifactInventory(
            run_name=request.run_name,
            exp_id=request.exp_id,
            model_type=request.model_type,
            relative_paths=(name,) if path.exists() else (),
        )


class LigoDataPath(PreparedRegressionDataPath):
    task_data_path_id: ClassVar[str] = "phyts_ligo_chirp_mass"


class Project8DataPath(PreparedRegressionDataPath):
    task_data_path_id: ClassVar[str] = "phyts_project8_energy"


class PreparedPredictionScoreability(ScoreabilityContract):
    contract_id: str = "prepared_scalar_predictions"

    def check(self, deliverables: Any) -> ScoreabilityVerdict:
        failures = []
        if not deliverables:
            failures.append(
                ScoreabilityFailure(
                    requirement="completeness", detail="no prediction artifact"
                )
            )
        for identity, path in deliverables.items():
            try:
                read_predictions(Path(path))
            except (OSError, ValueError, TypeError) as exc:
                failures.append(
                    ScoreabilityFailure(
                        requirement="format",
                        input_identity=int(identity),
                        detail=str(exc),
                    )
                )
        return ScoreabilityVerdict(
            contract_id=self.contract_id, failures=tuple(failures)
        )
