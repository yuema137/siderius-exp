"""Execute an already-admitted epoch using native validation and worker proxies.

The deployment owns request admission, scope/source/review identity checks and
worker isolation. This module never constructs candidate models or objectives.
It consumes task-owned data access only after those deployment checks.
"""

import math
import socket
from types import SimpleNamespace
from typing import Literal

import torch
from execute_tools.observables import DynamicObservableEpoch
from execute_tools.task_data_path import TaskDataPath
from execute_tools.train_engine_sandbox import observe_validation
from execute_tools.validation_execution import ValidationExecutionResult

from experiments.shared.validation_epoch_protocol import (
    ValidationBatchProgress,
    ValidationContinue,
    ValidationEpochMetadata,
)
from experiments.shared.validation_frames import read_frame, write_frame
from experiments.shared.validation_module_peer import ModulePeer
from experiments.shared.validation_rng import (
    capture_validation_rng,
    restore_validation_rng,
)


class ValidationProgressRelay:
    """Native verifier-shaped adapter; timing policy stays in the training client."""

    is_terminal = False

    def __init__(
        self,
        channel: socket.socket,
        *,
        sequence: int,
        expected_rows: int,
        deadline: float,
        max_metadata_bytes: int,
    ):
        self.channel = channel
        self.sequence = sequence
        self.expected_rows = expected_rows
        self.deadline = deadline
        self.max_metadata_bytes = max_metadata_bytes
        self.rows = 0

    def feed(self, unit_ms: float, *, elapsed_ms: float) -> None:
        if not math.isfinite(unit_ms) or unit_ms <= 0:
            raise ValueError("invalid native per-sample timing")
        if not math.isfinite(elapsed_ms) or elapsed_ms <= 0:
            raise ValueError("invalid native batch timing")
        count = elapsed_ms / unit_ms
        rows = round(count)
        if rows <= 0 or not math.isclose(count, rows, rel_tol=1e-9):
            raise ValueError("native timing does not identify a whole batch")
        if self.rows + rows > self.expected_rows:
            raise ValueError("validation batch exceeds admitted row count")
        event = ValidationBatchProgress(
            sequence=self.sequence, rows=rows, elapsed_ms=elapsed_ms
        )
        write_frame(
            self.channel.fileno(),
            event.model_dump_json().encode(),
            max_bytes=self.max_metadata_bytes,
            deadline=self.deadline,
        )
        reply = ValidationContinue.model_validate_json(
            read_frame(
                self.channel.fileno(),
                max_bytes=self.max_metadata_bytes,
                deadline=self.deadline,
            )
        )
        if reply.sequence != self.sequence:
            raise ValueError("validation acknowledgement sequence mismatch")
        self.rows += rows


def execute_admitted_epoch(
    request: ValidationEpochMetadata,
    *,
    model: ModulePeer,
    objective: ModulePeer,
    data_path: TaskDataPath,
    scope: object,
    data_dir: str,
    progress: ValidationProgressRelay,
    observables: DynamicObservableEpoch | None = None,
    resolved_custom_target_dtype: Literal["long", "float"] | None = None,
) -> ValidationExecutionResult:
    """Use the existing sample-weighted estimator; return aggregates only.

    The caller must supply the admitted task scope and a retained dynamic
    observable session if the frozen task declares any. No declaration or
    private-data permission is derived from client-provided metadata here.
    """
    if type(model) is not ModulePeer or type(objective) is not ModulePeer:
        raise TypeError("private validation requires numeric worker proxies")
    device = torch.device(request.device)
    if model.execution_device != device or objective.execution_device != device:
        raise ValueError("worker device differs from admitted epoch")
    if (
        progress.sequence != request.sequence
        or progress.expected_rows != request.expected_rows
        or progress.rows
    ):
        raise ValueError("progress relay differs from admitted epoch")
    devices = () if device.type == "cpu" else (device.index or 0,)
    if tuple(item.device for item in request.rng.torch_cuda) != devices:
        raise ValueError("epoch RNG devices differ from admitted device")
    original_rng = capture_validation_rng(cuda_devices=devices)
    observation = observables if observables is not None else DynamicObservableEpoch(())
    try:
        model.train(request.model_training)
        objective.train(request.objective_training)
        restore_validation_rng(request.rng)
        observation.start_epoch()
        value, rows, _ = observe_validation(
            model=model,
            criterion=objective,
            model_cfg=SimpleNamespace(model_type=request.model_type),
            loss_cfg=request.loss,
            model_io=request.model_io,
            device=device,
            data_path=data_path,
            task_eval_scope=scope,
            data_dir=data_dir,
            batch_size=request.batch_size,
            verifier=progress,
            observables=observation,
            resolved_custom_target_dtype=resolved_custom_target_dtype,
        )
        if rows != request.expected_rows or progress.rows != rows:
            raise ValueError("validation did not cover the admitted row count")
        values = observation.finish_epoch()
        return ValidationExecutionResult(
            r3=value,
            rows=rows,
            observables=values,
            failed_observables=tuple(observation.failures),
        )
    finally:
        restore_validation_rng(original_rng)
