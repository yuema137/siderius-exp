"""Coordinator-side nn.Module proxy; no candidate loading or code execution.

The caller owns worker launch, isolation, private stderr and whole-group cleanup.
The supplied monotonic deadline is continuing, never renewed by a call. All
post-call tensors and RNG state stay inside the private validation transaction.
"""

from __future__ import annotations

from typing import Annotated

import torch
from pydantic import Field, TypeAdapter

from experiments.shared.validation_frames import read_frame, write_frame
from experiments.shared.validation_module_protocol import (
    ModuleCall,
    ModuleFailure,
    ModuleResult,
    Operation,
    TensorPayload,
)
from experiments.shared.validation_rng import (
    capture_validation_rng,
    restore_validation_rng,
)

_REPLY = TypeAdapter(
    Annotated[ModuleResult | ModuleFailure, Field(discriminator="status")]
)


class ModulePeer(torch.nn.Module):
    def __init__(
        self,
        *,
        input_fd: int,
        output_fd: int,
        device: torch.device,
        deadline: float,
        max_frame_bytes: int,
    ):
        super().__init__()
        if device.type not in {"cpu", "cuda"} or (
            device.type == "cuda" and device.index is None
        ):
            raise ValueError(
                "validation worker requires CPU or an explicit CUDA device index"
            )
        self._input_fd = input_fd
        self._output_fd = output_fd
        self._device = device
        self._deadline = deadline
        self._max_frame_bytes = max_frame_bytes
        self._sequence = 0
        self._broken = False
        self._cuda = () if device.type == "cpu" else (device.index or 0,)
        self._call("describe")

    @property
    def execution_device(self) -> torch.device:
        return self._device

    def _call(self, operation: Operation, *, inputs=(), training=None) -> ModuleResult:
        if self._broken:
            raise RuntimeError("validation worker session is unusable")
        try:
            return self._exchange(operation, inputs=inputs, training=training)
        except (OSError, EOFError, ValueError, RuntimeError):
            self._broken = True
            raise

    def _exchange(
        self, operation: Operation, *, inputs=(), training=None
    ) -> ModuleResult:
        request = ModuleCall(
            sequence=self._sequence,
            operation=operation,
            rng=capture_validation_rng(cuda_devices=self._cuda),
            inputs=inputs,
            training=training,
        )
        write_frame(
            self._input_fd,
            request.model_dump_json().encode(),
            max_bytes=self._max_frame_bytes,
            deadline=self._deadline,
        )
        response = _REPLY.validate_json(
            read_frame(
                self._output_fd,
                max_bytes=self._max_frame_bytes,
                deadline=self._deadline,
            )
        )
        if isinstance(response, ModuleFailure):
            raise RuntimeError(f"validation worker refused: {response.code}")  # noqa: TRY004 -- valid protocol refusal, not an invalid Python type
        if response.sequence != self._sequence or response.operation != operation:
            raise ValueError("validation worker response identity mismatch")
        if tuple(item.device for item in response.rng.torch_cuda) != self._cuda:
            raise ValueError("validation worker response device mismatch")
        restore_validation_rng(response.rng)
        self.training = response.training
        self._sequence += 1
        return response

    def forward(self, *values: torch.Tensor) -> torch.Tensor:
        response = self._call(
            "forward", inputs=tuple(TensorPayload.capture(x) for x in values)
        )
        assert response.output is not None
        return response.output.tensor(device=self._device)

    def train(self, mode: bool = True):
        if self._broken:
            # Native validation restores mode in finally. A failed worker has
            # no usable remote module; restore this proxy's local flag without
            # masking the original failure with a second broken-pipe error.
            # Forward/state remain refused; this never revives a session.
            self.training = mode
            return self
        self._call("mode", training=mode)
        return self

    def state_dict(self, *args, **kwargs):
        if args or kwargs:
            raise ValueError(
                "validation proxy supports only the native no-argument state snapshot"
            )
        response = self._call("state")
        assert response.state is not None
        return {
            name: value.tensor(device=torch.device("cpu"))
            for name, value in response.state.items()
        }
