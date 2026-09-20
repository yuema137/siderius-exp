"""One epoch transaction on a protected launcher's inherited training channel.

The launcher constructs the workload from admitted native arguments after model
source and objective-review checks. Never derive it from the received request.
This module checks epoch routing before calling the private executor; it does not
establish OS confinement, issue training authority, or perform objective review.
"""

import socket
from collections.abc import Callable
from typing import Annotated

from agent.schemas.model_io_contract import ModelIOContract
from execute_tools.validation_execution import ValidationExecutionResult
from ml_models.models_format_sandbox import LossConfig
from pydantic import BaseModel, ConfigDict, Field, JsonValue, StrictInt

from experiments.shared.validation_descriptor_transport import receive_snapshots
from experiments.shared.validation_epoch_execution import ValidationProgressRelay
from experiments.shared.validation_epoch_protocol import (
    NativeValidationCancelled,
    ValidationEpochMetadata,
    ValidationEpochRefusal,
    ValidationEpochResult,
)
from experiments.shared.validation_frames import write_frame


class AdmittedValidationWorkload(BaseModel):
    """Immutable launch inputs; never accept these fields as client authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    model_type: str
    configuration: dict[str, JsonValue]
    model_io: ModelIOContract | None
    loss: LossConfig
    scope_payload: str
    device: str = Field(pattern=r"^(cpu|cuda:[0-9]+)$")
    batch_size: Annotated[StrictInt, Field(gt=0)]
    expected_rows: Annotated[StrictInt, Field(gt=0)]
    max_epochs: Annotated[StrictInt, Field(gt=0)]
    # Only assert an exact count when the operator has authoritative evidence.
    # Generic task datasets may vary in size across epochs. Native execution
    # already rejects zero-step epochs and owns sampling/drop_last/budget rules.
    # A guessed static count here must not become a second training restriction.
    optimizer_steps_per_epoch: Annotated[StrictInt, Field(gt=0)] | None = None

    def check(self, request: ValidationEpochMetadata, *, sequence: int) -> None:
        fields = type(self).model_fields.keys() - {
            "max_epochs",
            "optimizer_steps_per_epoch",
        }
        # Compare the entire declared workload, not just model name or row count.
        if self.model_dump(include=fields) != request.model_dump(include=fields):
            raise ValueError("epoch workload differs from admitted native invocation")
        facts = request.completed_training
        if (
            request.sequence != sequence
            or facts.completed_epochs != sequence + 1
            or facts.completed_epochs > self.max_epochs
            or (
                self.optimizer_steps_per_epoch is not None
                and facts.optimizer_steps != self.optimizer_steps_per_epoch
            )
        ):
            raise ValueError(
                "epoch progression differs from admitted native invocation"
            )


EpochExecutor = Callable[
    [ValidationEpochMetadata, tuple[int, int], ValidationProgressRelay],
    ValidationExecutionResult,
]


def serve_validation_epoch(
    channel: socket.socket,
    *,
    workload: AdmittedValidationWorkload,
    sequence: int,
    execute: EpochExecutor,
    deadline: float,
    max_metadata_bytes: int,
    max_snapshot_bytes: int,
) -> int:
    """Admit, execute with live progress, reply; never send exception text.

    The caller owns the native process lifetime and calls again only after a
    successful transaction. Received descriptors are closed on every exit.
    The executor launches confined workers using operator-bound source/review
    material and these snapshots, then calls execute_admitted_epoch. No weights
    are deserialized here, and failed transactions must not reuse the channel.
    """
    code = "not_admitted"
    try:
        with receive_snapshots(
            channel,
            deadline=deadline,
            max_metadata_bytes=max_metadata_bytes,
            max_snapshot_bytes=max_snapshot_bytes,
        ) as (payload, descriptors):
            request = ValidationEpochMetadata.model_validate_json(payload)
            workload.check(request, sequence=sequence)
            progress = ValidationProgressRelay(
                channel,
                sequence=sequence,
                expected_rows=workload.expected_rows,
                deadline=deadline,
                max_metadata_bytes=max_metadata_bytes,
            )
            code = "validation_failed"
            result = execute(request, descriptors, progress)
            if not isinstance(result, ValidationExecutionResult):
                raise TypeError("private executor returned an unvalidated result")
            if result.rows != workload.expected_rows or progress.rows != result.rows:
                raise ValueError("private executor returned incomplete validation")
            reply = ValidationEpochResult(sequence=sequence, result=result)
            write_frame(
                channel.fileno(),
                reply.model_dump_json().encode(),
                max_bytes=max_metadata_bytes,
                deadline=deadline,
            )
        return sequence + 1
    except NativeValidationCancelled:
        # No aggregate/result for this incomplete epoch; the child owns its
        # budget rejection record and is already unwinding its native call.
        raise
    except Exception as error:
        if isinstance(error, TimeoutError):
            code = "deadline_exhausted"
        try:
            refusal = ValidationEpochRefusal(sequence=sequence, code=code)
            write_frame(
                channel.fileno(),
                refusal.model_dump_json().encode(),
                max_bytes=max_metadata_bytes,
                deadline=deadline,
            )
        except (OSError, EOFError, TimeoutError, ValueError):
            pass
        # Retain the detailed failure in the private launcher, never the reply.
        raise
