"""Check saved tutorial resource settings without keys, task loading or training."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import psutil
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from experiments.shared.framework_pin import (
    verify_framework_pin,
    verify_installed_framework,
)
from tutorials.shared.gpu_check import ExpectedGpu, VramBudget
from tutorials.shared.runtime import ROOT, gpu_report


class HardwareSettings(BaseModel):
    """Resource projection only; task runners own complete experiment validation."""

    model_config = ConfigDict(frozen=True, extra="ignore")
    infra_checkout: Path
    workspace: Path
    vram_gib: VramBudget
    gpu: ExpectedGpu | None = None
    trial_vram_gib: VramBudget | None = None
    formal_vram_gib: VramBudget | None = None

    @field_validator("infra_checkout", "workspace")
    @classmethod
    def absolute_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("hardware bindings must use absolute paths")
        return value.resolve()


def host_observations(workspace: Path) -> dict:
    """Observe the host and target filesystem without claiming workload sufficiency."""
    target = workspace
    while not target.exists() and target != target.parent:
        target = target.parent
    if not target.is_dir():
        raise ValueError("Workspace or its existing parent must be a directory")
    if not os.access(target, os.W_OK | os.X_OK):
        raise ValueError(f"Output directory is not writable/searchable: {target}")
    disk = shutil.disk_usage(target)
    try:
        memory = psutil.virtual_memory()
        memory_values = {
            "total_bytes": memory.total,
            "available_bytes": memory.available,
        }
    except (OSError, ValueError, NotImplementedError):
        memory_values = None
    return {
        "host_ram": memory_values,
        "job_ram_allowance": "unknown; host figures do not establish container/job limits",
        "output_filesystem": str(target),
        "output_free_bytes": disk.free,
        "required_output_bytes": "unknown; generated checkpoints and results vary",
    }


def inspect_hardware(settings: HardwareSettings) -> dict:
    """Verify the selected pair, then perform only disclosed hardware observations."""
    revision = verify_framework_pin(ROOT, settings.infra_checkout)
    verify_installed_framework(revision, ROOT)
    host = host_observations(settings.workspace)
    report = gpu_report(settings)
    return {
        "scope": "hardware resource projection only; not full experiment/task/key validation",
        "infra_revision": revision,
        "gpu": report.model_dump(mode="json"),
        "host": host,
        "limitations": [
            "Snapshot only: no GPU reservation, model-fit proof or lasting headroom guarantee.",
            "Configured caps are allowances, not measured model requirements.",
            "Host RAM and free disk are observations, not workload admission checks.",
            "No provider calls, training, data downloads or run outputs were created.",
        ],
    }


def main() -> None:
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    args = parser.parse_args()
    try:
        settings = HardwareSettings.model_validate_json(args.experiment.read_text())
    except ValidationError as error:
        fields = ", ".join(
            ".".join(map(str, item["loc"])) or "JSON"
            for item in error.errors(include_input=False)
        )
        raise ValueError(
            f"Invalid saved hardware settings: {fields}. Supply absolute infra_checkout "
            "and workspace paths and an explicit positive finite vram_gib; optional "
            "Trial/Formal overrides must also be positive and finite."
        ) from None
    print(json.dumps(inspect_hardware(settings), indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        sys.exit(f"Tutorial hardware check refused: {error}")
    except subprocess.SubprocessError:
        sys.exit(
            "Tutorial hardware check refused: cannot verify the selected source pair."
        )
