"""Adapt native trained models to the unchanged TIDMAD baseline candidate format."""

import shutil
from pathlib import Path
from typing import Literal

import numpy as np
import torch
from execute_tools.evaluation_execution import CandidateEvaluationRequest
from pydantic import BaseModel, ConfigDict, Field

from deployments.tidmad_coding_agent_baseline.tools.segment_inference import (
    SEGMENT_SIZE,
    SegmentModelContract,
    _decode,
    load_candidate_model,
)
from experiments.shared.native_model_export import export_native_model
from tasks.tidmad.runtime.output_conversion import regression_to_storage


class NativeTidmadExporter(BaseModel):
    """Explicit serialization choice; export runs as the research account."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    method: Literal["script", "trace"]
    inference_batch_size: int = Field(default=32, ge=1, le=32)
    execution_devices: tuple[str, ...] = ("cpu",)

    def __call__(self, request: CandidateEvaluationRequest, destination: Path) -> None:
        contract = SegmentModelContract(
            version="tidmad-segment-model-v2",
            segment_size=SEGMENT_SIZE,
            input_dtype="int64",
            output_kind="continuous_regression",
            inference_batch_size=self.inference_batch_size,
        )
        examples = [
            (torch.zeros(1, SEGMENT_SIZE, dtype=torch.int64),),
            (
                torch.arange(
                    self.inference_batch_size * SEGMENT_SIZE, dtype=torch.int64
                ).reshape(self.inference_batch_size, SEGMENT_SIZE)
                % 256,
            ),
        ]
        export_native_model(
            request,
            destination,
            examples=examples,
            method=self.method,
            execution_devices=self.execution_devices,
        )
        try:
            (destination / "architecture.json").write_text(
                contract.model_dump_json(indent=2) + "\n"
            )
            restored, _ = load_candidate_model(destination, torch.device("cpu"))
            # Reuse the frozen evaluator's tensor/output checks and public
            # conversion on synthetic raw inputs; no task data is opened.
            for args in examples:
                raw = (args[0].numpy() - 128).astype(np.int8)
                _decode(
                    restored, raw, torch.device("cpu"), contract, regression_to_storage
                )
        except BaseException:
            shutil.rmtree(destination)
            raise
