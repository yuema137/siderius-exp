"""Executable data path for event-level SuperNEMO classification."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import torch
from torch.utils.data import Dataset

from execute_tools.task_data_path import (
    DeliverableWriteRequest,
    EpochSamplingParams,
    EvalMaterializationParams,
    EvaluationReadRequest,
    ScopeBuildRequest,
    TaskOutputArtifactInventory,
    register_task_data_path,
)

from ._supernemo_data import (
    SuperNemoEventDataset,
    SuperNemoScope,
    materialize_scope,
)


class SuperNemoTaskDataPath:
    task_data_path_id: ClassVar[str] = "supernemo_signal_background"
    _SCOPE_KIND: ClassVar[str] = "supernemo_scope_v1"

    @staticmethod
    def _build(request: ScopeBuildRequest, role: str) -> SuperNemoScope:
        if request.selection_strategy != "snapshot":
            raise ValueError("SuperNEMO supports deterministic snapshot scopes only")
        return SuperNemoScope(
            role=role,
            portion=request.portion,
            seed=request.seed,
            max_samples=request.max_samples,
        )

    def build_training_scope(self, request: ScopeBuildRequest) -> object:
        return self._build(request, "train")

    def build_eval_scope(self, request: ScopeBuildRequest) -> object:
        return self._build(request, "validation")

    def serialize_scope(self, scope: object) -> str:
        return json.dumps(
            {"kind": self._SCOPE_KIND, "scope": self._scope(scope).model_dump()},
            sort_keys=True,
            separators=(",", ":"),
        )

    def deserialize_scope(self, payload: str) -> object:
        value = json.loads(payload)
        if value.get("kind") != self._SCOPE_KIND:
            raise ValueError("serialized SuperNEMO scope has the wrong kind")
        return SuperNemoScope.model_validate(value["scope"])

    @staticmethod
    def _scope(scope: object) -> SuperNemoScope:
        if not isinstance(scope, SuperNemoScope):
            raise TypeError("SuperNEMO data path requires a SuperNemoScope")
        return scope

    def training_dataset(self, scope: object, params: EpochSamplingParams) -> Dataset[Any]:
        train_portion = params.train_portion or 1.0
        events = materialize_scope(self._scope(scope), params.data_dir, train_portion)
        return SuperNemoEventDataset(events, params.data_dir)

    def validation_dataset(self, scope: object, params: EvalMaterializationParams) -> Dataset[Any]:
        events = materialize_scope(self._scope(scope), params.data_dir)
        return SuperNemoEventDataset(events, params.data_dir)

    def write_deliverable(self, outputs: Iterable[Any], request: DeliverableWriteRequest) -> None:
        path = Path(request.output_dir) / deliverable_name(request)
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write("row_index,signal_probability\n")
            for row_index, output in enumerate(outputs):
                tensor = torch.as_tensor(output).detach().float().flatten()
                if tensor.numel() != 2:
                    raise ValueError("SuperNEMO classifier output must have two logits")
                probability = float(torch.softmax(tensor, dim=0)[1])
                handle.write(f"{row_index},{probability:.10g}\n")

    def read_evaluation_payload(self, request: EvaluationReadRequest) -> object:
        path = Path(request.deliverable_dir) / deliverable_name(request)
        if not path.exists():
            return np.array([], dtype=np.float64)
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0] != "row_index,signal_probability":
            raise ValueError("invalid SuperNEMO classification deliverable header")
        values = []
        for expected, line in enumerate(lines[1:]):
            row, score = line.split(",")
            if int(row) != expected:
                raise ValueError("SuperNEMO deliverable row order is not contiguous")
            values.append(float(score))
        return np.asarray(values, dtype=np.float64)

    def enumerate_output_artifacts(
        self, request: EvaluationReadRequest
    ) -> TaskOutputArtifactInventory:
        """List the exact attempt CSV, including a partially written file."""
        name = deliverable_name(request)
        path = Path(request.deliverable_dir) / name
        return TaskOutputArtifactInventory(
            run_name=request.run_name,
            exp_id=request.exp_id,
            model_type=request.model_type,
            relative_paths=(name,) if path.exists() or path.is_symlink() else (),
        )


def deliverable_name(request: DeliverableWriteRequest | EvaluationReadRequest) -> str:
    return f"predictions_{request.model_type}_{request.run_name}_{request.exp_id}.csv"


register_task_data_path(SuperNemoTaskDataPath())
