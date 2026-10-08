"""Process bindings and checks shared by task-owned tutorial launchers."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Protocol

from tutorials.shared.gpu_check import (
    GPU_CHECK_RESPONSE,
    GpuCheckRequest,
)

ROOT = Path(__file__).resolve().parents[2]


class RuntimeSettings(Protocol):
    """Read-only resource bindings; each tutorial owns its experiment schema."""

    @property
    def workspace(self) -> Path: ...
    @property
    def infra_checkout(self) -> Path: ...
    @property
    def gpu(self) -> str | None: ...
    @property
    def vram_gib(self) -> float: ...
    @property
    def trial_vram_gib(self) -> float | None: ...
    @property
    def formal_vram_gib(self) -> float | None: ...


def disjoint(left: Path, right: Path) -> bool:
    """Reject equality and either direction of nesting after symlink resolution."""
    left, right = left.resolve(), right.resolve()
    return not (left.is_relative_to(right) or right.is_relative_to(left))


def verify_gpu(settings: RuntimeSettings) -> str:
    """Run the launch-only check in infra's environment, without source overlays."""
    python = settings.infra_checkout / ".venv/bin/python"
    if not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError(
            f"Missing executable infra Python: {python}. Run uv sync --group dev "
            "--frozen in that checkout before launch."
        )
    request = GpuCheckRequest(
        expected_name=settings.gpu,
        trial_vram_gib=settings.trial_vram_gib
        if settings.trial_vram_gib is not None
        else settings.vram_gib,
        formal_vram_gib=settings.formal_vram_gib
        if settings.formal_vram_gib is not None
        else settings.vram_gib,
    )
    try:
        result = subprocess.run(
            [str(python), str(Path(__file__).with_name("gpu_check.py"))],
            input=request.model_dump_json(),
            env=child_environment(settings),
            cwd=settings.infra_checkout,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError(
            "GPU setup check failed or exceeded 60 seconds in the selected infra "
            "environment. Verify the qualified source pair, run uv sync --group dev "
            "--frozen there, and check driver/device access. Child stderr is omitted "
            "to avoid exposing inherited environment details."
        ) from error
    try:
        report = GPU_CHECK_RESPONSE.validate_json(result.stdout)
    except ValueError as error:
        raise ValueError(
            "GPU setup check returned an invalid report. Reinstall the qualified "
            "infra/exp pair in their own frozen environments."
        ) from error
    if report.status == "failed":
        raise ValueError(report.message)
    details = (
        f"{report.device_name}; logical device {report.logical_index}; "
        f"{report.capacity_gib:g} GiB; backend {report.installed_backend}; "
        "kernel witness passed; live admission/accounting checks still required"
    )
    return details + (
        "; " + "; ".join(report.limitations) if report.limitations else ""
    )


def child_environment(settings: RuntimeSettings) -> dict[str, str]:
    """Keep credentials in the environment and bind generated artifacts to this run."""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name in (
        "PYTHONPATH",
        "SIDERIUS_PLUGIN_DIRS",
        "AGENT_GENERATED_DIR",
        "SIDERIUS_MODEL_PLUGIN_PATH",
        "SIDERIUS_LOSS_PLUGIN_PATH",
        "SIDERIUS_LOSS_DIRS",
    ):
        env.pop(name, None)
    env.update(
        {
            "SIDERIUS_GENERATED_LIBRARY_DIR": str(
                settings.workspace / "generated_library"
            ),
            "SIDERIUS_CHAIN_WORKSPACE": str(settings.workspace),
            "SIDERIUS_CALIBRATION_DIR": str(settings.workspace / "calibration"),
        }
    )
    return env


def composition_identity(settings: RuntimeSettings, manifest: str) -> str:
    """Resolve with the infra environment and run-local plugins, never user defaults."""
    result = subprocess.run(
        [
            str(settings.infra_checkout / ".venv/bin/python"),
            "-c",
            (
                "import sys; "
                "from workflows.task_composition import compose_run_task_bindings; "
                "print(compose_run_task_bindings(sys.argv[1]).semantic_fingerprint)"
            ),
            manifest,
        ],
        cwd=settings.infra_checkout,
        env=child_environment(settings),
        check=True,
        capture_output=True,
        text=True,
    )
    fingerprint = result.stdout.strip().splitlines()[-1]
    if re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise ValueError("composition resolver returned no valid fingerprint")
    return fingerprint
