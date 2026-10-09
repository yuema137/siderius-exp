"""Executable data path for the NatureBench cancer-gene task.

Each biological network is one transductive sample. The single model tensor
contains node records followed by edge records, keeping graph topology and
multi-omics features together without teaching the framework graph vocabulary.
"""

from __future__ import annotations

import hashlib
import json
import math
import secrets
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar, Literal

import h5py
import numpy as np
import torch
from agent.schemas.model_probe import ModelProbeRequest
from execute_tools.task_data_path import (
    DeliverableWriteRequest,
    EpochSamplingParams,
    EvalMaterializationParams,
    EvaluationReadRequest,
    ScopeBuildRequest,
    TaskOutputArtifactInventory,
    ValidationScopeError,
)
from pydantic import BaseModel, ConfigDict, Field
from torch.utils.data import Dataset

CANCER_GENE_TASK_ID = "naturebench_cancer_gene"
INSTANCES = ("cpdb", "stringdb", "pcnet", "iref_v15", "iref_v9", "multinet", "mtg", "ltg")
RECORD_WIDTH = 68


class CancerGeneScope(BaseModel):
    """Task-owned scope: selected networks and the label split to evaluate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    instances: tuple[str, ...] = Field(min_length=1)
    evaluation_split: Literal["val", "test"] = "val"
    active_fraction: float = Field(default=1.0, gt=0.0, le=1.0)
    sampling_seed: int = Field(default=0, ge=0)
    max_active_nodes: int | None = Field(default=None, ge=1)

    def sampled_mask(self, mask: np.ndarray, *, network: str, split: str) -> np.ndarray:
        """Select active nodes without changing the task-owned split boundary."""
        active = np.flatnonzero(np.asarray(mask, dtype=bool).reshape(-1))
        if active.size == 0:
            raise ValueError(f"{network} {split} mask contains no active nodes")
        keep = max(1, int(np.ceil(active.size * self.active_fraction)))
        if self.max_active_nodes is not None:
            keep = min(keep, self.max_active_nodes)
        if keep < active.size:
            digest = hashlib.sha256(f"{self.sampling_seed}:{network}:{split}".encode()).digest()
            rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
            active = np.sort(rng.choice(active, size=keep, replace=False))
        selected = np.zeros(np.asarray(mask).size, dtype=bool)
        selected[active] = True
        return selected


class _GraphDataset(Dataset[Any]):
    def __init__(
        self,
        scope: CancerGeneScope,
        data_dir: str,
        target_split: Literal["train", "val", "test"],
        *,
        active_fraction: float | None = None,
        sampling_seed: int | None = None,
        max_active_nodes: int | None = None,
    ):
        self._scope = scope
        self._data_dir = Path(data_dir)
        self._target_split = target_split
        self._active_fraction = (
            scope.active_fraction if active_fraction is None else active_fraction
        )
        self._sampling_seed = scope.sampling_seed if sampling_seed is None else sampling_seed
        self._max_active_nodes = (
            scope.max_active_nodes if max_active_nodes is None else max_active_nodes
        )
        missing = [
            name for name in scope.instances if not (self._data_dir / name / "data.h5").is_file()
        ]
        if missing:
            raise ValidationScopeError(
                f"cancer-gene scope names missing data.h5 files under {self._data_dir}: {missing}"
            )

    def __len__(self) -> int:
        return len(self._scope.instances)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        name = self._scope.instances[index]
        path = self._data_dir / name / "data.h5"
        with h5py.File(path, "r") as handle:
            features = np.asarray(handle["features"], dtype=np.float32)
            node_count = features.shape[0]
            rows: list[np.ndarray] = []
            cols: list[np.ndarray] = []
            network = handle["network"]
            for start in range(0, node_count, 2048):
                block = np.asarray(network[start : start + 2048])
                row, col = np.nonzero(block)
                keep = row + start != col
                rows.append((row[keep] + start).astype(np.int64, copy=False))
                cols.append(col[keep].astype(np.int64, copy=False))
            edge_src = np.concatenate(rows) if rows else np.empty(0, dtype=np.int64)
            edge_dst = np.concatenate(cols) if cols else np.empty(0, dtype=np.int64)

            packed = np.zeros((node_count + len(edge_src), RECORD_WIDTH), dtype=np.float32)
            packed[:node_count, 0] = 1.0
            packed[:node_count, 1] = np.arange(node_count, dtype=np.float32)
            packed[:node_count, 4:] = features
            packed[node_count:, 1] = edge_src.astype(np.float32)
            packed[node_count:, 2] = edge_dst.astype(np.float32)

            target = np.full((node_count + len(edge_src), 3), -1.0, dtype=np.float32)
            target[:, 0] = packed[:, 0]
            if self._target_split != "test":
                sampling_scope = self._scope.model_copy(
                    update={
                        "active_fraction": self._active_fraction,
                        "sampling_seed": self._sampling_seed,
                        "max_active_nodes": self._max_active_nodes,
                    }
                )
                mask = sampling_scope.sampled_mask(
                    np.asarray(handle[f"mask_{self._target_split}"]),
                    network=name,
                    split=self._target_split,
                )
                labels = np.asarray(handle[f"y_{self._target_split}"], dtype=np.float32).reshape(-1)
                packed[:node_count, 3] = mask.astype(np.float32)
                target[:node_count, 2][mask] = labels[mask]
            else:
                mask = np.asarray(handle["mask_test"]).astype(bool).reshape(-1)
                packed[:node_count, 3] = mask.astype(np.float32)
            target[:, 1] = packed[:, 3]
        return torch.from_numpy(packed), torch.from_numpy(target)


def deliverable_name(request: DeliverableWriteRequest | EvaluationReadRequest) -> str:
    return f"cancer_gene_predictions_{request.model_type}_{request.run_name}_{request.exp_id}.json"


class CancerGeneTaskDataPath:
    """Out-of-tree implementation of the task data and scope contracts."""

    task_data_path_id: ClassVar[str] = CANCER_GENE_TASK_ID
    _SCOPE_KIND: ClassVar[str] = "naturebench_cancer_gene_scope_v1"

    @staticmethod
    def model_validation_input(request: ModelProbeRequest) -> torch.Tensor:
        """Build a legal synthetic graph for CPU candidate checks, without data I/O."""
        shape = request.input_shape
        if len(shape) != 3 or shape[0] != 1 or shape[2] != RECORD_WIDTH:
            raise ValueError("Cancer candidate probes require shape [1, R, 68]")
        if request.dtype != "float32":
            raise ValueError("Cancer candidate probes require float32 inputs")
        records = shape[1]
        # n*n >= R provides enough distinct non-self edges for R-n edge rows.
        nodes = math.isqrt(records - 1) + 1
        packed = torch.zeros(shape, dtype=torch.float32)
        packed[0, :nodes, 0] = 1
        packed[0, :nodes, 1] = torch.arange(nodes)
        packed[0, :nodes, 3] = (torch.arange(nodes) % 2 == 0).float()
        packed[0, :nodes, 4:] = torch.linspace(0, 1, RECORD_WIDTH - 4)
        edges = records - nodes
        if edges:
            index = torch.arange(edges)
            source = index // (nodes - 1)
            destination = index % (nodes - 1)
            destination = destination + (destination >= source).long()
            packed[0, nodes:, 1] = source
            packed[0, nodes:, 2] = destination
        return packed

    @staticmethod
    def custom_loss_validation_pair() -> tuple[torch.Tensor, torch.Tensor]:
        """Return a tiny labeled-node pair without reading NatureBench data."""
        prediction = torch.tensor([[[1.0, 1.0, 0.25], [0.0, 1.0, 0.0]]], dtype=torch.float32)
        target = torch.tensor([[[1.0, 1.0, 1.0], [0.0, 1.0, -1.0]]], dtype=torch.float32)
        return prediction, target

    def __init__(
        self,
        instances: Sequence[str] = INSTANCES,
        evaluation_split: Literal["val", "test"] = "val",
    ) -> None:
        unknown = sorted(set(instances) - set(INSTANCES))
        if unknown:
            raise ValueError(f"unknown cancer-gene network instances: {unknown}")
        self._instances = tuple(instances)
        self._evaluation_split = evaluation_split

    def _select(self, request: ScopeBuildRequest) -> tuple[str, ...]:
        candidates = list(self._instances)
        if request.subset_ref is not None:
            requested = tuple(
                part.strip() for part in request.subset_ref.split(",") if part.strip()
            )
            unknown = sorted(set(requested) - set(candidates))
            if unknown:
                raise ValueError(f"subset_ref names unknown cancer-gene networks: {unknown}")
            candidates = [name for name in candidates if name in requested]
        if request.selection_strategy == "target":
            try:
                candidates = [candidates[index] for index in request.target_partitions]
            except IndexError as exc:
                raise ValueError(
                    "target_partitions contains an out-of-range network index"
                ) from exc
        return tuple(candidates)

    @staticmethod
    def _scope_from_request(
        instances: tuple[str, ...],
        request: ScopeBuildRequest,
        evaluation_split: Literal["val", "test"],
    ) -> CancerGeneScope:
        seed = request.seed if request.seed is not None else secrets.randbits(32)
        return CancerGeneScope(
            instances=instances,
            evaluation_split=evaluation_split,
            active_fraction=request.portion,
            sampling_seed=seed,
            max_active_nodes=request.max_samples,
        )

    def build_training_scope(self, request: ScopeBuildRequest) -> object:
        return self._scope_from_request(self._select(request), request, self._evaluation_split)

    def build_eval_scope(self, request: ScopeBuildRequest) -> object:
        return self._scope_from_request(self._select(request), request, self._evaluation_split)

    def max_inference_batch_size(self) -> int:
        """Whole-network records have variable lengths and cannot be stacked."""
        return 1

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
            raise ValueError("payload is not a naturebench_cancer_gene_scope_v1 scope")
        return CancerGeneScope.model_validate(raw["scope"])

    @staticmethod
    def _scope(scope: object) -> CancerGeneScope:
        if not isinstance(scope, CancerGeneScope):
            raise TypeError(
                f"cancer-gene data path requires CancerGeneScope, got {type(scope).__name__}"
            )
        return scope

    def training_dataset(self, scope: object, params: EpochSamplingParams) -> Dataset[Any]:
        checked = self._scope(scope)
        return _GraphDataset(
            checked,
            params.data_dir,
            "train",
            active_fraction=params.train_portion,
            sampling_seed=params.epoch_seed,
            max_active_nodes=params.max_samples,
        )

    def validation_dataset(self, scope: object, params: EvalMaterializationParams) -> Dataset[Any]:
        checked = self._scope(scope)
        return _GraphDataset(checked, params.data_dir, checked.evaluation_split)

    def write_deliverable(self, outputs: Any, request: DeliverableWriteRequest) -> None:
        scope = self._scope(request.task_scope)
        sequence = list(outputs)
        if len(sequence) != len(scope.instances):
            raise ValueError(
                f"cancer-gene deliverable received {len(sequence)} outputs for "
                f"{len(scope.instances)} network instances"
            )
        root = Path(request.output_dir) / deliverable_name(request).removesuffix(".json")
        root.mkdir(parents=True, exist_ok=True)
        manifest: dict[str, str] = {}
        for name, prediction in zip(scope.instances, sequence, strict=True):
            tensor = torch.as_tensor(prediction)
            if tensor.ndim != 2 or tensor.shape[1] != 3:
                raise ValueError(
                    "cancer-gene model output must be [records, 3]: "
                    "node marker, evaluation marker, logit"
                )
            node_mask = tensor[:, 0] > 0.5
            evaluation_mask = tensor[:, 1] > 0.5
            selected = node_mask & evaluation_mask
            probabilities = torch.sigmoid(tensor[selected, 2]).numpy().astype(np.float32)
            target_dir = root / name
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / "predictions.npy"
            np.save(target, probabilities)
            manifest[name] = str(target.relative_to(Path(request.output_dir)))
        payload = {
            "format": "naturebench_cancer_gene_predictions_v1",
            "evaluation_split": scope.evaluation_split,
            "files": manifest,
        }
        (Path(request.output_dir) / deliverable_name(request)).write_text(
            json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8"
        )

    def read_evaluation_payload(self, request: EvaluationReadRequest) -> object:
        manifest_path = Path(request.deliverable_dir) / deliverable_name(request)
        if not manifest_path.is_file():
            return {}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format") != "naturebench_cancer_gene_predictions_v1":
            raise ValueError(f"{manifest_path} has an unknown cancer-gene deliverable format")
        return {
            name: np.load(Path(request.deliverable_dir) / relative)
            for name, relative in manifest["files"].items()
        }

    def enumerate_output_artifacts(
        self, request: EvaluationReadRequest
    ) -> TaskOutputArtifactInventory:
        """List this attempt's manifest and any partially written nested arrays."""
        root = Path(request.deliverable_dir)
        manifest_name = deliverable_name(request)
        manifest_path = root / manifest_name
        arrays_root = root / manifest_name.removesuffix(".json")
        paths = [manifest_name] if manifest_path.exists() or manifest_path.is_symlink() else []
        if arrays_root.is_dir() and not arrays_root.is_symlink():
            paths.extend(
                str(path.relative_to(root))
                for path in arrays_root.rglob("*")
                if path.is_file() or path.is_symlink()
            )
        elif arrays_root.exists() or arrays_root.is_symlink():
            # A non-directory attempt root is not a valid output; the generic
            # validator will refuse it rather than ignore suspicious bytes.
            paths.append(str(arrays_root.relative_to(root)))
        return TaskOutputArtifactInventory(
            run_name=request.run_name,
            exp_id=request.exp_id,
            model_type=request.model_type,
            relative_paths=tuple(sorted(paths)),
        )
