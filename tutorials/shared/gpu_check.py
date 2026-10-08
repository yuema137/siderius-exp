"""Launch-only GPU setup check, executed by the selected framework interpreter.

Importing this module only defines the JSON boundary. Framework discovery and
the tiny kernel witness run only through check_gpu; preview never calls it.
"""

from __future__ import annotations

import sys
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter

ExpectedGpu = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
VramBudget = Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]


class GpuCheckRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    expected_name: ExpectedGpu | None = None
    trial_vram_gib: VramBudget
    formal_vram_gib: VramBudget


class GpuCheckReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: Literal["passed"] = "passed"
    installed_backend: Literal["cuda", "rocm"]
    runtime_version: str | None
    device_name: str
    logical_index: Literal[0] = 0
    capacity_gib: VramBudget
    device_uuid: str
    limitations: tuple[str, ...]
    driver_queries_passed: Literal[True] = True
    kernel_witness: Literal[True] = True


class GpuCheckFailure(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: Literal["failed"] = "failed"
    message: str


GPU_CHECK_RESPONSE = TypeAdapter(
    Annotated[GpuCheckReport | GpuCheckFailure, Field(discriminator="status")]
)


def check_gpu(request: GpuCheckRequest) -> GpuCheckReport:
    """Check required facts before allocation; actual admission still owns samples."""
    try:
        from core.hardware_context import inspect_gpu_runtime
    except ImportError as error:
        raise ValueError(
            "The selected framework lacks inspect_gpu_runtime. Use the qualified "
            "infra/exp revision pair and each checkout's own frozen environment; "
            "do not change only one pin or borrow another environment."
        ) from error

    try:
        facts = inspect_gpu_runtime()
    except Exception as error:
        raise ValueError(
            f"GPU property discovery failed ({type(error).__name__}). Check GPU "
            "access in this job/container and the selected infra's frozen PyTorch installation."
        ) from error
    hardware = facts.hardware
    if facts.installed_backend == "none" or not hardware.device_available:
        raise ValueError(
            "No usable CUDA/ROCm device is visible to the selected infra interpreter. "
            "Check its installed backend and job/container device access; CPU and Intel "
            "GPU training are not supported by this tutorial."
        )
    if hardware.visible_device_count != 1:
        raise ValueError(
            "Select exactly one visible logical GPU for this tutorial, for example "
            "with CUDA_VISIBLE_DEVICES before launch. Physical GPU numbering is not "
            "the logical index used inside the job."
        )
    if (
        request.expected_name is not None
        and request.expected_name not in hardware.device_name
    ):
        raise ValueError(
            f"Expected GPU name containing {request.expected_name!r}; observed "
            f"{hardware.device_name!r}. Update gpu in your saved experiment JSON "
            "or set it to null to use the selected visible device."
        )
    capacity = hardware.total_memory_bytes / 1024**3
    if capacity <= max(request.trial_vram_gib, request.formal_vram_gib):
        raise ValueError(
            "VRAM budget must be below physical capacity. Lower vram_gib or its "
            "trial_vram_gib/formal_vram_gib overrides in your saved experiment JSON."
        )
    if facts.implemented_accounting_adapter is None:
        raise ValueError(
            f"{facts.installed_backend} driver/process GPU accounting is not implemented. "
            "This tutorial requires that resource protection, so it cannot launch on "
            "this backend. AMD/ROCm compatibility is experimental and untested; "
            "do not disable required protection to proceed."
        )
    from core.runtime_control.gpu_accounting import (
        device_identity_from_hardware,
        sample_device_baseline,
    )

    identity = device_identity_from_hardware(hardware)
    if identity is None:
        raise ValueError(
            "Stable driver GPU identity is unavailable. Check the driver and device "
            "visibility in this job/container. Required accounting cannot use a "
            "model name or logical index as an identity."
        )
    try:
        baseline = sample_device_baseline(identity)
    except Exception as error:
        raise ValueError(
            f"GPU driver queries failed ({type(error).__name__}). Check driver tooling "
            "and device/process query access inside this job/container before launch."
        ) from error
    if not baseline.telemetry_available:
        raise ValueError(
            "GPU driver device/process queries are unavailable. Check driver tooling "
            "and permissions inside this job/container; required accounting must work "
            "before allocation or provider calls. Do not disable resource protection."
        )
    try:
        import torch

        torch.zeros(1, device="cuda:0").add_(1)
        torch.cuda.synchronize(0)
    except Exception as error:
        raise ValueError(
            f"GPU kernel witness failed ({type(error).__name__}). Check driver/backend "
            "compatibility and free GPU memory in the selected infra environment. "
            "Keep the qualified frozen installation; do not swap individual wheels."
        ) from error
    return GpuCheckReport(
        installed_backend=facts.installed_backend,
        runtime_version=facts.runtime_version,
        device_name=hardware.device_name,
        capacity_gib=capacity,
        device_uuid=identity.uuid,
        limitations=facts.limitations,
    )


def main() -> None:
    try:
        request = GpuCheckRequest.model_validate_json(sys.stdin.read())
    except ValueError:
        result = GpuCheckFailure(
            message="Invalid GPU setup request; check saved resource settings."
        )
    else:
        try:
            result = check_gpu(request)
        except ValueError as error:
            result = GpuCheckFailure(message=str(error))
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
