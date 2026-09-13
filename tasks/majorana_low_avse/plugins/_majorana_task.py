"""Executable data path for Majorana Low-AvsE waveform classification."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import torch
from execute_tools.task_data_path import (
    DeliverableWriteRequest,
    EpochSamplingParams,
    EvalMaterializationParams,
    EvaluationReadRequest,
    ScopeBuildRequest,
    register_task_data_path,
)
from torch.utils.data import Dataset

from ._majorana_data import MajoranaScope, MajoranaWaveformDataset, materialize_scope


class MajoranaTaskDataPath:
    task_data_path_id: ClassVar[str] = "majorana_low_avse"
    _SCOPE_KIND: ClassVar[str] = "majorana_low_avse_scope_v1"

    @staticmethod
    def _build(request: ScopeBuildRequest, role: str) -> MajoranaScope:
        if request.selection_strategy != "snapshot":
            raise ValueError("Majorana supports deterministic snapshot scopes only")
        return MajoranaScope(
            role=role,
            portion=request.portion,
            seed=request.seed,
            max_samples=request.max_samples,
        )

    def build_training_scope(self, request: ScopeBuildRequest) -> object:
        return self._build(request, "train")

    def build_eval_scope(self, request: ScopeBuildRequest) -> object:
        return self._build(request, "test")

    def serialize_scope(self, scope: object) -> str:
        checked = self._scope(scope)
        return json.dumps(
            {"kind": self._SCOPE_KIND, "scope": checked.model_dump()}, sort_keys=True
        )

    def deserialize_scope(self, payload: str) -> object:
        value = json.loads(payload)
        if value.get("kind") != self._SCOPE_KIND:
            raise ValueError("serialized Majorana scope has the wrong kind")
        return MajoranaScope.model_validate(value["scope"])

    @staticmethod
    def _scope(scope: object) -> MajoranaScope:
        if not isinstance(scope, MajoranaScope):
            raise TypeError("Majorana data path requires a MajoranaScope")
        return scope

    def training_dataset(
        self, scope: object, params: EpochSamplingParams
    ) -> Dataset[Any]:
        events = materialize_scope(
            self._scope(scope), params.data_dir, params.train_portion or 1.0
        )
        return MajoranaWaveformDataset(events, params.data_dir)

    def validation_dataset(
        self, scope: object, params: EvalMaterializationParams
    ) -> Dataset[Any]:
        events = materialize_scope(self._scope(scope), params.data_dir)
        return MajoranaWaveformDataset(events, params.data_dir)

    def write_deliverable(
        self, outputs: Iterable[Any], request: DeliverableWriteRequest
    ) -> None:
        path = Path(request.output_dir) / deliverable_name(request)
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write("row_index,accepted_probability\n")
            for row_index, output in enumerate(outputs):
                logits = torch.as_tensor(output).detach().float().flatten()
                if logits.numel() != 2:
                    raise ValueError("Majorana classifier output must have two logits")
                probability = float(torch.softmax(logits, dim=0)[1])
                handle.write(f"{row_index},{probability:.10g}\n")

    def read_evaluation_payload(self, request: EvaluationReadRequest) -> object:
        path = Path(request.deliverable_dir) / deliverable_name(request)
        if not path.exists():
            return np.array([], dtype=np.float64)
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0] != "row_index,accepted_probability":
            raise ValueError("invalid Majorana classification deliverable header")
        values = []
        for expected, line in enumerate(lines[1:]):
            row, score = line.split(",")
            if int(row) != expected:
                raise ValueError("Majorana deliverable row order is not contiguous")
            values.append(float(score))
        return np.asarray(values, dtype=np.float64)


def deliverable_name(request: DeliverableWriteRequest | EvaluationReadRequest) -> str:
    return f"predictions_{request.model_type}_{request.run_name}_{request.exp_id}.csv"


register_task_data_path(MajoranaTaskDataPath())
