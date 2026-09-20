"""Research-side epoch exchange on a launcher-owned inherited channel.

The caller supplies task-owned scope serialization and row declaration. Row
declaration is also needed in the native parent before the training child exists;
it must not require this child's inherited descriptor or private sample reads.
This class does not install a public factory or authenticate caller claims.
"""

import os
import socket
import time
from collections.abc import Callable
from typing import Annotated

from execute_tools.training_budget_execution import TrainingAllocationRejected
from execute_tools.validation_execution import (
    ValidationCallbacks,
    ValidationExecutionRequest,
    ValidationExecutionResult,
)
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StrictInt, TypeAdapter

from experiments.shared.validation_descriptor_transport import send_snapshots
from experiments.shared.validation_epoch_protocol import (
    ValidationBatchProgress,
    ValidationCancelled,
    ValidationContinue,
    ValidationEpochMetadata,
    ValidationEpochRefusal,
    ValidationEpochResult,
)
from experiments.shared.validation_frames import read_frame, write_frame
from experiments.shared.validation_rng import (
    capture_validation_rng,
    resolve_validation_device,
)
from experiments.shared.validation_snapshot import sealed_tensor_state

_REPLY = TypeAdapter(
    Annotated[
        ValidationBatchProgress | ValidationEpochResult | ValidationEpochRefusal,
        Field(discriminator="kind"),
    ]
)


class InheritedClientSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    channel_fd: Annotated[StrictInt, Field(ge=0)]
    deadline_epoch: FiniteFloat
    max_metadata_bytes: Annotated[StrictInt, Field(ge=1024)]
    max_state_bytes: Annotated[StrictInt, Field(gt=0)]


class InheritedValidationClient:
    def __init__(
        self,
        settings: InheritedClientSettings,
        *,
        serialize_scope: Callable[[object], str],
        declare_rows: Callable[[object], int],
    ):
        self.settings = InheritedClientSettings.model_validate_json(
            settings.model_dump_json()
        )
        self.channel = socket.socket(fileno=settings.channel_fd)
        os.set_inheritable(settings.channel_fd, False)
        self.deadline = time.monotonic() + max(
            0.0, settings.deadline_epoch - time.time()
        )
        self.serialize_scope = serialize_scope
        self.declare_rows = declare_rows
        self.sequence = 0
        self.broken = False

    def declared_rows(self, scope: object) -> int:
        return self.declare_rows(scope)

    def close(self) -> None:
        self.broken = True
        self.channel.close()

    def observe(
        self,
        request: ValidationExecutionRequest,
        callbacks: ValidationCallbacks,
    ) -> ValidationExecutionResult:
        if self.broken:
            raise RuntimeError("validation channel is closed")
        try:
            if callbacks.check_allocation is not None:
                callbacks.check_allocation()
            if time.monotonic() >= self.deadline:
                raise TimeoutError("validation invocation deadline exhausted")
            device = resolve_validation_device(request.device)
            cuda_devices = ()
            if device.type == "cuda":
                assert device.index is not None
                cuda_devices = (device.index,)
            metadata = ValidationEpochMetadata(
                sequence=self.sequence,
                model_type=request.model_type,
                configuration=request.configuration.model_dump(mode="json"),
                completed_training=request.completed_training,
                model_io=request.model_io,
                loss=request.loss,
                scope_payload=self.serialize_scope(request.scope),
                device=str(device),
                batch_size=request.batch_size,
                expected_rows=request.expected_rows,
                model_training=request.model.training,
                objective_training=request.criterion.training,
                rng=capture_validation_rng(cuda_devices=cuda_devices),
            )
            with (
                sealed_tensor_state(
                    request.model.state_dict(),
                    max_tensor_bytes=self.settings.max_state_bytes,
                ) as model,
                sealed_tensor_state(
                    request.criterion.state_dict(),
                    max_tensor_bytes=self.settings.max_state_bytes,
                ) as objective,
            ):
                send_snapshots(
                    self.channel,
                    metadata.model_dump_json().encode(),
                    [model.fd, objective.fd],
                    deadline=self.deadline,
                    max_metadata_bytes=self.settings.max_metadata_bytes,
                )
                result = self._receive(request, callbacks)
            self.sequence += 1
            return result
        except BaseException:
            self.close()
            raise

    def _receive(self, request, callbacks) -> ValidationExecutionResult:
        rows = 0
        verifier = callbacks.verifier
        while True:
            reply = _REPLY.validate_json(
                read_frame(
                    self.channel.fileno(),
                    max_bytes=self.settings.max_metadata_bytes,
                    deadline=self.deadline,
                )
            )
            if reply.sequence != self.sequence:
                raise ValueError("validation reply sequence mismatch")
            if isinstance(reply, ValidationEpochRefusal):
                raise RuntimeError(f"validation refused: {reply.code}")  # noqa: TRY004 -- typed service refusal, not a bad Python type
            try:
                if callbacks.check_allocation is not None:
                    callbacks.check_allocation()
                if isinstance(reply, ValidationEpochResult):
                    if rows != request.expected_rows or reply.result.rows != rows:
                        raise ValueError(
                            "validation progress/result rows differ from declaration"
                        )
                    return reply.result
                rows += reply.rows
                if rows > request.expected_rows:
                    raise ValueError("validation progress exceeds declared rows")
                if verifier is not None:
                    verifier.feed(
                        reply.elapsed_ms / reply.rows, elapsed_ms=reply.elapsed_ms
                    )
                    if verifier.is_terminal:
                        if callbacks.on_verified is not None:
                            callbacks.on_verified()
                        verifier = None
            except TrainingAllocationRejected:
                # Preserve the native rejection/sidecar; explicitly release the
                # server waiting for an acknowledgement instead of causing EOF.
                if isinstance(reply, ValidationBatchProgress):
                    try:
                        write_frame(
                            self.channel.fileno(),
                            ValidationCancelled(sequence=self.sequence)
                            .model_dump_json()
                            .encode(),
                            max_bytes=self.settings.max_metadata_bytes,
                            deadline=self.deadline,
                        )
                    except (OSError, EOFError, TimeoutError, ValueError):
                        pass  # A broken channel must not replace the budget cause.
                raise
            # The server waits for this acknowledgement before the next batch,
            # so refreshed native deadlines are visible during the pass.
            write_frame(
                self.channel.fileno(),
                ValidationContinue(sequence=self.sequence).model_dump_json().encode(),
                max_bytes=self.settings.max_metadata_bytes,
                deadline=self.deadline,
            )
