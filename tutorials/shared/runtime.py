"""Process bindings and checks shared by task-owned tutorial launchers."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[2]


class RuntimeSettings(Protocol):
    """Read-only resource bindings; each tutorial owns its experiment schema."""

    @property
    def workspace(self) -> Path: ...
    @property
    def infra_checkout(self) -> Path: ...
    @property
    def gpu(self) -> str: ...
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
    """Require one supported physical GPU and a working CUDA allocation in infra."""
    try:
        probe = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise ValueError(
            "NVIDIA GPU detection failed. Run nvidia-smi in this terminal; install/enable the NVIDIA driver "
            "and GPU access for this container/job. AMD and Intel GPUs are unsupported."
        ) from error
    rows = probe.stdout.strip().splitlines()
    if len(rows) != 1 or settings.gpu not in rows[0]:
        raise ValueError(
            f"expected one {settings.gpu}; observed {rows}. Set gpu in your saved experiment JSON to the actual supported device (RTX 5090 or H100). Other NVIDIA devices need the hardware adaptation described in the README; AMD/Intel are unsupported."
        )
    capacity_gib = float(rows[0].rsplit(",", 1)[1].strip()) / 1024
    if (
        max(
            settings.trial_vram_gib or settings.vram_gib,
            settings.formal_vram_gib or settings.vram_gib,
        )
        >= capacity_gib
    ):
        raise ValueError(
            "VRAM budget must be below physical capacity, leaving driver/runtime headroom. Lower vram_gib (and trial_vram_gib/formal_vram_gib if set) in your saved experiment JSON."
        )
    try:
        subprocess.run(
            [
                str(settings.infra_checkout / ".venv/bin/python"),
                "-c",
                (
                    "import torch; assert torch.version.hip is None; "
                    "assert torch.cuda.is_available(); torch.empty(1, device='cuda'); "
                    "torch.cuda.synchronize()"
                ),
            ],
            check=True,
            env=child_environment(settings),
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(
            f"CUDA allocation failed in {settings.infra_checkout}. "
            "Run uv sync --group dev --frozen in the infra checkout, verify its own PyTorch CUDA installation "
            "and NVIDIA driver, and free GPU memory before retrying."
        ) from error
    return rows[0]


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
