"""Persistent numeric call loop inside an already-confined module worker.

The launcher owns module construction, account/mount/network isolation and
whole-process cleanup. No candidate code is loaded in the private coordinator.
"""

import sys
import time
import traceback

import torch

from experiments.shared.validation_frames import read_frame, write_frame
from experiments.shared.validation_module_protocol import (
    ModuleCall,
    ModuleFailure,
    ModuleResult,
    TensorPayload,
)
from experiments.shared.validation_rng import (
    capture_validation_rng,
    restore_validation_rng,
)


def execute_call(
    module: torch.nn.Module, request: ModuleCall, *, role: str, device: torch.device
) -> ModuleResult:
    """Candidate calls stay here, never in the private coordinator."""
    if request.operation == "forward" and len(request.inputs) != (
        1 if role == "model" else 2
    ):
        raise ValueError("input count differs from worker role")
    devices = () if device.type == "cpu" else (device.index or 0,)
    if tuple(item.device for item in request.rng.torch_cuda) != devices:
        raise ValueError("RNG devices differ from worker device")
    restore_validation_rng(request.rng)
    output, state = None, None
    with torch.no_grad():
        if request.operation == "forward":
            values = tuple(item.tensor(device=device) for item in request.inputs)
            output = TensorPayload.capture(module(*values))
        elif request.operation == "mode":
            module.train(request.training)
        elif request.operation == "state":
            state = {
                name: TensorPayload.capture(value)
                for name, value in module.state_dict().items()
            }
    return ModuleResult(
        sequence=request.sequence,
        operation=request.operation,
        rng=capture_validation_rng(cuda_devices=devices),
        training=module.training,
        output=output,
        state=state,
    )


def serve_module(
    module: torch.nn.Module,
    *,
    role: str,
    device: torch.device,
    input_fd: int,
    output_fd: int,
    deadline: float,
    max_frame_bytes: int,
) -> int:
    """Reuse one initialized module for all calls until EOF/failure/deadline."""
    if role not in {"model", "objective"}:
        raise ValueError("unknown validation module role")

    def reply(result):
        write_frame(
            output_fd,
            result.model_dump_json().encode(),
            max_bytes=max_frame_bytes,
            deadline=deadline,
        )

    sequence = 0
    while time.monotonic() < deadline:
        try:
            payload = read_frame(input_fd, max_bytes=max_frame_bytes, deadline=deadline)
        except EOFError:
            return 0
        except (TimeoutError, OSError, ValueError):
            return 1
        try:
            request = ModuleCall.model_validate_json(payload)
            if request.sequence != sequence:
                raise ValueError("request sequence mismatch")
        except ValueError:
            reply(ModuleFailure(code="invalid_request"))
            return 1
        try:
            result = execute_call(module, request, role=role, device=device)
        except Exception:  # noqa: BLE001 -- arbitrary candidate failures are bounded protocol refusals
            traceback.print_exc(file=sys.stderr)
            # Raw tracebacks/output remain private; no candidate exception text
            # is serialized into the result channel.
            reply(ModuleFailure(code="execution_failed"))
            return 1
        reply(result)
        sequence += 1
    return 1
