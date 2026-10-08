"""Explicit GPU setup check, executed by the selected framework interpreter.

Importing this module only defines the JSON boundary. Framework discovery and
the tiny kernel witness run only through check_gpu; preview never calls it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
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
    occupied_gib: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    trial_vram_gib: VramBudget
    formal_vram_gib: VramBudget
    configured_cap_gib: VramBudget
    effective_ceiling_gib: VramBudget
    remaining_after_cap_gib: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    host_quota_gib: VramBudget | None
    operator_ceiling_gib: VramBudget | None
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
    """Check configured-cap readiness; native model admission remains independent."""
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
            "VRAM budget must be below physical capacity. Select a larger GPU or "
            "deliberately lower vram_gib or its trial_vram_gib/formal_vram_gib "
            "overrides and use a smaller model/workload. Lowering a budget alone "
            "does not make a model fit."
        )
    if facts.implemented_accounting_adapter is None:
        raise ValueError(
            f"{facts.installed_backend} driver/process GPU accounting is not implemented. "
            "This tutorial requires that resource protection, so it cannot launch on "
            "this backend. AMD/ROCm compatibility is experimental and untested; "
            "do not disable required protection to proceed."
        )
    from core.runtime_control.gpu_accounting import (
        OccupancyBound,
        device_identity_from_hardware,
        sample,
    )
    from core.runtime_control.pair_admission import (
        PairMember,
        evaluate_resolved_pair_admission,
        gib_from_mib,
        resolve_gpu_ceiling,
    )

    identity = device_identity_from_hardware(hardware)
    if identity is None:
        raise ValueError(
            "Stable driver GPU identity is unavailable. Check the driver and device "
            "visibility in this job/container. Required accounting cannot use a "
            "model name or logical index as an identity."
        )
    try:
        baseline = sample(os.getpid(), identity)
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
        if baseline.device != identity:
            raise ValueError("GPU identity mismatch")
        occupancy = OccupancyBound.model_validate(
            {name: getattr(baseline, name) for name in OccupancyBound.model_fields}
        )
    except (ValueError, AttributeError) as error:
        raise ValueError(
            "GPU occupancy queries are missing or inconsistent. Retry the hardware "
            "check when device/process queries are stable; do not treat unknown "
            "usage as free memory or disable protection."
        ) from error
    occupied = gib_from_mib(occupancy.device_used_mib)
    configured_cap = max(request.trial_vram_gib, request.formal_vram_gib)
    try:
        limits = resolve_gpu_ceiling(
            measured_capacity_gib=min(
                capacity, gib_from_mib(occupancy.device_total_mib)
            )
        )
        members = [
            PairMember(
                run_name="tutorial",
                predicted_peak_vram_gb=configured_cap,
                provenance="largest sequential phase configured cap; not measured model demand",
            )
        ]
        if occupied:
            members.append(
                PairMember(
                    run_name="current_device_occupancy",
                    predicted_peak_vram_gb=occupied,
                    provenance="all current device usage, including unattributed memory",
                )
            )
        decision = evaluate_resolved_pair_admission(members, limits=limits)
    except ValueError as error:
        raise ValueError(
            "Invalid GPU ceiling or quota. Check SIDERIUS_PAIR_VRAM_CEILING_GIB "
            "(GiB) and SIDERIUS_GPU_VRAM_QUOTA_MIB (MiB): declared values must be "
            "positive and finite. Ask the deployment owner before changing a quota."
        ) from error
    if not decision.feasible:
        raise ValueError(
            f"Insufficient GPU headroom for the configured allowance: {occupied:g} GiB "
            f"already occupied + {configured_cap:g} GiB largest Trial/Formal cap exceeds "
            f"the effective {decision.ceiling_gib:g} GiB ceiling. Wait for other work, "
            "select another GPU, or deliberately lower your saved VRAM allowance and "
            "use a smaller model. The check does not change budgets or reserve memory."
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
        occupied_gib=occupied,
        trial_vram_gib=request.trial_vram_gib,
        formal_vram_gib=request.formal_vram_gib,
        configured_cap_gib=configured_cap,
        effective_ceiling_gib=decision.ceiling_gib,
        remaining_after_cap_gib=decision.headroom_gib,
        host_quota_gib=limits.host_quota_gib,
        operator_ceiling_gib=limits.operator_ceiling_gib,
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
            from core import hardware_context

            checkout = Path.cwd()
            if (
                Path(sys.prefix).resolve() != (checkout / ".venv").resolve()
                or Path(hardware_context.__file__).resolve()
                != (checkout / "src/core/hardware_context.py").resolve()
            ):
                raise ValueError(
                    "Selected infra Python loads a different environment or checkout. "
                    "Run uv sync --group dev --frozen in the selected infra checkout."
                )
            result = check_gpu(request)
        except ImportError:
            result = GpuCheckFailure(
                message="Selected infra installation is incomplete. Run uv sync "
                "--group dev --frozen in the selected checkout and verify the "
                "qualified infra/exp revision pair."
            )
        except ValueError as error:
            result = GpuCheckFailure(message=str(error))
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
