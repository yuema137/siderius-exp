"""Executable data path for the PhyTS TESS near-core rotation task.

One TESS light curve is one sample. The model receives a single normalized
flux channel of fixed length and predicts one scalar rotation frequency in
cycles per day; the run's primary metric is R-squared and HIGHER is better.

**Two sources, deliberately.** Scope CONSTRUCTION reads the committed
identity manifest beside this file: ``ScopeBuildRequest`` carries no physical
data root, and pinning the population in Git means a run's split cannot drift
with whatever happens to sit in ``--data_dir``. Scope MATERIALIZATION reads
the staged archive under ``params.data_dir``. The manifest is the authority
for *which curves and what targets*; the staged archive is the authority for
*the flux samples themselves*.

**Why the test split cannot be reached from here.** :data:`TessSplit` admits
``train`` and ``val`` only, so a scope naming the held-out final-evaluation
split is not a value this module can construct or deserialize, and the
committed manifest carries no test row or test target. That is a
declaration. The operative filesystem isolation is that the staging tool
never copies the test split into a run's ``--data_dir``. Both are needed
and neither alone is sufficient — see ``../data/README.md``.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, ClassVar, Literal

import numpy as np
import torch
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
from pydantic import BaseModel, ConfigDict, Field
from torch.utils.data import Dataset

PHYTS_TESS_TASK_ID = "phyts_tess_rotation"

#: The two splits a SIDERIUS run may touch. ``test`` is deliberately absent:
#: it is the held-out final-evaluation population, and no composed run,
#: training scope, evaluation scope or Health peek may reach it.
TessSplit = Literal["train", "val"]

#: Frozen input length, PhyTS appendix D.2 parity. Released curves run
#: 542..3917 samples, so both the truncate and the pad branch below are
#: exercised by the real dataset rather than being defensive dead code.
SEQUENCE_LENGTH = 1024

#: A run's ``--data_dir`` holds exactly these two files.
#:
#: NPZ rather than the released parquet, and the reason is a dependency
#: boundary rather than a preference: reading parquet needs ``pyarrow``,
#: which this repository does not declare, and a per-epoch reparse of a
#: variable-length list column is slower than a memory-mapped archive
#: anyway. The staging tool performs the one-time conversion and verifies
#: the result against the committed identity manifest. RAW flux is stored —
#: ``normalize_curve`` below remains the single preprocessing authority, so
#: staging cannot silently become a second one.
SPLIT_FILENAME = "tess_rotation_{split}.npz"


class TessRow(BaseModel):
    """One light curve's identity and its supervised target.

    ``(gaia_id, sector)`` is the row key. It is unique within every released
    split — ``(tic, sector)`` is NOT unique in train, which is why the TESS
    Input Catalogue identifier is not keyed on here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    gaia_id: int
    sector: int
    frot: float

    @property
    def key(self) -> str:
        """Stable, order-independent identity used by the deliverable."""
        return f"{self.gaia_id}:{self.sector}"


class TessScope(BaseModel):
    """Task-owned scope: which light curves, from which split.

    The scope carries its targets because it IS the run's ground-truth
    authority — the metric reads truth from here rather than re-reading a
    parquet, so the denominator can never drift from the population the
    scoreability contract already validated.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    split: TessSplit
    rows: tuple[TessRow, ...] = Field(min_length=1)
    sequence_length: int = Field(default=SEQUENCE_LENGTH, ge=1)

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(row.key for row in self.rows)

    def truth(self) -> dict[str, float]:
        return {row.key: row.frot for row in self.rows}


def _split_path(data_dir: str, split: TessSplit) -> Path:
    return Path(data_dir) / SPLIT_FILENAME.format(split=split)


def normalize_curve(flux: np.ndarray, sequence_length: int) -> np.ndarray:
    """Frozen preprocessing: right-truncate or last-value pad, then z-score.

    Order matters and is part of the task definition. Padding BEFORE the
    z-score would let a short curve's pad value shift its own mean; this
    normalizes the observed samples and then extends with the last observed
    value, which is the PhyTS appendix D.2 rule.

    A constant curve has zero standard deviation. It normalizes to all zeros
    rather than raising: a flat light curve is a real, if uninformative,
    observation and not a malformed one, so the metric is entitled to see
    whatever the model answers for it.
    """
    observed = np.asarray(flux, dtype=np.float64).reshape(-1)
    if observed.size == 0:
        raise ValidationScopeError("a TESS light curve carries zero flux samples")
    if observed.size > sequence_length:
        observed = observed[:sequence_length]
    mean = float(observed.mean())
    std = float(observed.std())
    centred = observed - mean
    scaled = centred / std if std > 0.0 else np.zeros_like(centred)
    if scaled.size < sequence_length:
        scaled = np.concatenate(
            [
                scaled,
                np.full(sequence_length - scaled.size, scaled[-1], dtype=np.float64),
            ]
        )
    return scaled.astype(np.float32, copy=False)


def _load_flux(
    data_dir: str, split: TessSplit, keys: tuple[str, ...]
) -> dict[str, np.ndarray]:
    """Read the requested light curves' raw flux, keyed by ``gaia_id:sector``.

    Only the scope's own keys are decompressed. An npz member is decoded
    lazily on access, so a trial round drawing a small portion does not pay
    for the whole split.
    """
    path = _split_path(data_dir, split)
    if not path.is_file():
        raise ValidationScopeError(
            f"PhyTS TESS {split} split is not present at {path}. A run's --data_dir "
            "must contain the staged train and val archives; the pack's "
            "data/README.md carries the staging command."
        )
    with np.load(path) as handle:
        available = set(handle.files)
        missing = [key for key in keys if key not in available]
        if missing:
            raise ValidationScopeError(
                f"PhyTS TESS {split} scope names {len(missing)} light curves the "
                f"staged archive does not contain, first: {missing[0]}"
            )
        return {key: np.asarray(handle[key], dtype=np.float64) for key in keys}


class _TessCurveDataset(Dataset[Any]):
    """Materializes exactly the rows a scope declares, in scope order."""

    def __init__(self, scope: TessScope, data_dir: str) -> None:
        self._scope = scope
        self._curves = _load_flux(data_dir, scope.split, scope.keys)

    def __len__(self) -> int:
        return len(self._scope.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self._scope.rows[index]
        curve = normalize_curve(self._curves[row.key], self._scope.sequence_length)
        return torch.from_numpy(curve).unsqueeze(0), torch.tensor(
            [row.frot], dtype=torch.float32
        )


def deliverable_name(request: DeliverableWriteRequest | EvaluationReadRequest) -> str:
    """Module-level, because that is what the framework actually looks for.

    ``task_names_its_own_deliverables`` inspects the MODULE the data-path
    class is defined in; a staticmethod of the same name would not satisfy
    it, and omitting both this and a ``deliverable:`` section is refused at
    compose time.
    """
    return (
        f"tess_rotation_{request.model_type}_{request.run_name}_{request.exp_id}.json"
    )


class PhytsTessTaskDataPath:
    """Out-of-tree implementation of the data-path and scope contracts."""

    task_data_path_id: ClassVar[str] = PHYTS_TESS_TASK_ID
    _SCOPE_KIND: ClassVar[str] = "phyts_tess_rotation_scope_v1"
    _DELIVERABLE_FORMAT: ClassVar[str] = "phyts_tess_rotation_predictions_v1"

    def __init__(
        self, manifest_path: str, sequence_length: int = SEQUENCE_LENGTH
    ) -> None:
        if sequence_length < 1:
            raise ValueError(f"sequence_length must be positive; got {sequence_length}")
        self._manifest_path = Path(manifest_path)
        self._sequence_length = sequence_length
        self._catalog: dict[TessSplit, tuple[TessRow, ...]] = {}

    # ----------------------------------------------------------------- scope

    def _rows(self, split: TessSplit) -> tuple[TessRow, ...]:
        """One split's population, from the committed manifest, read once.

        Rows are sorted by ``(gaia_id, sector)`` so that a scope built twice
        from the same request is byte-identical after serialization — the
        framework hashes that payload to verify scope transport.
        """
        cached = self._catalog.get(split)
        if cached is not None:
            return cached
        if not self._manifest_path.is_file():
            raise ValidationScopeError(
                f"PhyTS TESS identity manifest is missing at {self._manifest_path}"
            )
        with self._manifest_path.open(newline="", encoding="utf-8") as handle:
            records = [
                TessRow(
                    gaia_id=int(entry["gaia_id"]),
                    sector=int(entry["sector"]),
                    frot=float(entry["frot"]),
                )
                for entry in csv.DictReader(handle)
                if entry["split"] == split
            ]
        if not records:
            raise ValidationScopeError(
                f"PhyTS TESS identity manifest declares no {split!r} rows"
            )
        rows = tuple(sorted(records, key=lambda row: (row.gaia_id, row.sector)))
        self._catalog[split] = rows
        return rows

    def _build(self, request: ScopeBuildRequest, split: TessSplit) -> TessScope:
        if request.subset_ref is not None:
            raise ValueError(
                "PhyTS TESS declares no partition-subset vocabulary, so "
                f"subset_ref={request.subset_ref!r} (the generic --data_scope) cannot be "
                "honoured. Reduce `portion` instead."
            )
        if request.selection_strategy == "target" and request.target_partitions:
            raise ValueError(
                "PhyTS TESS exposes one partition per split, so an explicit "
                "target_partitions selection has nothing to name."
            )
        return TessScope(
            split=split,
            rows=self._sample(self._rows(split), request, split),
            sequence_length=self._sequence_length,
        )

    @staticmethod
    def _sample(
        rows: tuple[TessRow, ...], request: ScopeBuildRequest, split: TessSplit
    ) -> tuple[TessRow, ...]:
        """Draw a reproducible subset, keeping every star's curves together.

        The draw is over STARS, not rows. The released splits are grouped by
        Gaia DR3 identifier so no star appears in two splits; drawing
        individual rows would preserve that between-split property while
        silently splitting one star's curves across a round's train and eval
        draws. Grouping here keeps the task's independence rule true at every
        portion, not only at 1.0.
        """
        if request.portion >= 1.0:
            selected = rows
        else:
            keep = max(1, int(np.ceil(len(rows) * request.portion)))
            stars = sorted({row.gaia_id for row in rows})
            counts: dict[int, int] = {}
            for row in rows:
                counts[row.gaia_id] = counts.get(row.gaia_id, 0) + 1
            rng = np.random.default_rng(
                np.array(
                    [
                        request.seed if request.seed is not None else 0,
                        len(stars),
                        len(rows),
                    ],
                    dtype=np.uint64,
                )
            )
            chosen: set[int] = set()
            taken = 0
            for position in rng.permutation(len(stars)):
                star = stars[int(position)]
                chosen.add(star)
                taken += counts[star]
                if taken >= keep:
                    break
            selected = tuple(row for row in rows if row.gaia_id in chosen)
        if request.max_samples is not None and len(selected) > request.max_samples:
            selected = selected[: request.max_samples]
        if not selected:
            raise ValueError(
                f"PhyTS TESS {split} selection produced zero light curves at "
                f"portion={request.portion}"
            )
        return selected

    def build_training_scope(self, request: ScopeBuildRequest) -> object:
        return self._build(request, "train")

    def build_eval_scope(self, request: ScopeBuildRequest) -> object:
        return self._build(request, "val")

    # ------------------------------------------------------------ transport

    def serialize_scope(self, scope: object) -> str:
        checked = self._scope(scope)
        return json.dumps(
            {"kind": self._SCOPE_KIND, "scope": checked.model_dump(mode="json")},
            sort_keys=True,
            separators=(",", ":"),
        )

    def deserialize_scope(self, payload: str) -> object:
        raw = json.loads(payload)
        if set(raw) != {"kind", "scope"} or raw["kind"] != self._SCOPE_KIND:
            raise ValueError(f"payload is not a {self._SCOPE_KIND} scope")
        return TessScope.model_validate(raw["scope"])

    @staticmethod
    def _scope(scope: object) -> TessScope:
        if not isinstance(scope, TessScope):
            raise TypeError(
                f"PhyTS TESS requires TessScope, got {type(scope).__name__}"
            )
        return scope

    # ------------------------------------------------------------- datasets

    def training_dataset(
        self, scope: object, params: EpochSamplingParams
    ) -> Dataset[Any]:
        checked = self._scope(scope)
        if checked.split != "train":
            raise ValidationScopeError(
                f"a training dataset was requested over the {checked.split!r} split; "
                "PhyTS TESS trains on train only."
            )
        return _TessCurveDataset(checked, params.data_dir)

    def validation_dataset(
        self, scope: object, params: EvalMaterializationParams
    ) -> Dataset[Any]:
        return _TessCurveDataset(self._scope(scope), params.data_dir)

    def max_inference_batch_size(self) -> int:
        """Fixed-length single-channel curves stack cleanly under 8 GiB."""
        return 256

    def validate_health_coverage(
        self, request: HealthCoverageRequest
    ) -> HealthCoverageResult:
        """Can THIS attempt's evaluation scope support the task's Health demand?

        Required, not optional, once a composed run has Health enabled: the
        framework refuses to execute an attempt whose task declines to answer.

        The demand is one generic dispersion check over the predicted rotation
        frequencies, so coverage is a question about the ESTIMATOR rather than
        about files. Population dispersion over a single value is identically
        zero, which the floor would read as a collapse that is really an
        artefact of the scope; two values is the smallest scope on which the
        statistic means anything at all. A larger scope is noisier-to-less-noisy,
        not covered-to-uncovered, so it is not a second threshold here.
        """
        binding = request.health_binding
        if binding is None:
            return HealthCoverageResult(
                applicable=False,
                covered=False,
                reason="no Health family is bound for this attempt",
            )
        if request.health_gate_files is not None:
            return HealthCoverageResult(
                applicable=True,
                covered=False,
                reason=(
                    "a monitored-file override was supplied, but PhyTS TESS "
                    "exposes one partition per split and has no monitored-file "
                    "vocabulary to interpret it with"
                ),
            )
        scope = request.evaluation_scope
        rows = getattr(scope, "rows", None)
        if rows is None:
            return HealthCoverageResult(
                applicable=True,
                covered=False,
                reason=(
                    "Health coverage needs a PhyTS TESS evaluation scope; got "
                    f"{type(scope).__name__}, which declares no rows"
                ),
            )
        if len(rows) < 2:
            return HealthCoverageResult(
                applicable=True,
                covered=False,
                reason=(
                    f"the evaluation scope holds {len(rows)} light curve(s); the "
                    "prediction-dispersion check is identically zero below two "
                    "and would report a collapse that is an artefact of the scope"
                ),
            )
        return HealthCoverageResult(
            applicable=True,
            covered=True,
            reason=(
                f"{len(rows)} light curves in the {scope.split} scope support the "
                "prediction-dispersion check"
            ),
        )

    def storage_read_scope(self, data_dir: str, scope: object) -> StorageReadScope:
        path = _split_path(data_dir, self._scope(scope).split).resolve()
        return StorageReadScope(
            file_paths=(str(path),),
            expected_on_disk_bytes=path.stat().st_size if path.is_file() else 0,
        )

    # ---------------------------------------------------------- deliverable

    def write_deliverable(self, outputs: Any, request: DeliverableWriteRequest) -> None:
        scope = self._scope(request.task_scope)
        sequence = [float(torch.as_tensor(value).reshape(-1)[0]) for value in outputs]
        if len(sequence) != len(scope.rows):
            raise ValueError(
                f"PhyTS TESS deliverable received {len(sequence)} predictions for "
                f"{len(scope.rows)} light curves"
            )
        target = Path(request.output_dir) / deliverable_name(request)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "format": self._DELIVERABLE_FORMAT,
                    "split": scope.split,
                    "predictions": dict(zip(scope.keys, sequence, strict=True)),
                },
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )

    def read_evaluation_payload(self, request: EvaluationReadRequest) -> object:
        path = Path(request.deliverable_dir) / deliverable_name(request)
        if not path.is_file():
            return {}
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("format") != self._DELIVERABLE_FORMAT:
            raise ValueError(f"{path} has an unknown PhyTS TESS deliverable format")
        return {
            str(key): float(value) for key, value in manifest["predictions"].items()
        }

    def enumerate_output_artifacts(
        self, request: EvaluationReadRequest
    ) -> TaskOutputArtifactInventory:
        root = Path(request.deliverable_dir)
        name = deliverable_name(request)
        path = root / name
        return TaskOutputArtifactInventory(
            run_name=request.run_name,
            exp_id=request.exp_id,
            model_type=request.model_type,
            relative_paths=(name,) if path.exists() or path.is_symlink() else (),
        )
