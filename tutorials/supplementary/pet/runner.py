"""Preview or execute saved Pet inputs through the native fixed workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from experiments.shared.fixed_workflow_config import render_siderius_args
from experiments.shared.framework_pin import (
    verify_framework_pin,
    verify_installed_framework,
)
from experiments.shared.workflow_credentials import required_workflow_api_keys
from tutorials.shared.planner_setup import verify_planner_setup
from tutorials.shared.runtime import (
    ROOT,
    child_environment,
    composition_identity,
    disjoint,
    verify_gpu,
)
from tutorials.supplementary.pet.data import inspect_data
from tutorials.supplementary.pet.settings import PetExperiment


def validate_locations(settings: PetExperiment) -> None:
    for path in (
        settings.workspace,
        settings.data_dir,
        settings.composition,
        settings.llm_config,
        settings.workflow,
    ):
        if any(not disjoint(path, repo) for repo in (ROOT, settings.infra_checkout)):
            raise ValueError(
                "data, editable inputs and outputs must be outside both source checkouts"
            )
    if not disjoint(settings.workspace, settings.data_dir):
        raise ValueError("run workspace must be separate from the image directory")
    if settings.workspace.exists():
        raise ValueError(
            "run workspace already exists; inspect it and save a new run name/path before relaunching"
        )
    for path in (settings.composition, settings.llm_config, settings.workflow):
        if not path.is_file():
            raise ValueError(
                f"Missing saved input: {path}. Restore it in your external project."
            )
        if not disjoint(path, settings.workspace) or not disjoint(
            path, settings.data_dir
        ):
            raise ValueError(
                "saved configuration must be outside the data and output directories"
            )


def build_command(settings: PetExperiment) -> list[str]:
    validate_locations(settings)
    # The workflow is a user-owned copy; its relative paths resolve in that project.
    project = settings.workflow.parent.parent
    args = render_siderius_args(
        settings.workflow,
        repository_root=project,
        siderius_checkout=settings.infra_checkout,
    )
    values = {
        "--task_composition": settings.composition,
        "--llm_config": settings.llm_config,
        "--num_iterations": settings.iterations,
        "--max_rounds": settings.rounds,
        "--max_epochs": settings.epochs,
        "--trial_max_epochs": settings.epochs,
        "--formal_max_epochs": settings.epochs,
        "--trial_portion": settings.trial_train_fraction,
        "--eval_portion": settings.trial_val_fraction,
        "--formal_portion": settings.formal_train_fraction,
        "--formal_eval_portion": settings.formal_val_fraction,
        "--train_portion": settings.train_portion,
        "--formal_train_portion": settings.train_portion,
        "--trial_time_budget_minutes": settings.trial_minutes,
        "--formal_time_budget_minutes": settings.formal_minutes,
        "--trial_vram_budget_gb": settings.trial_vram_gib or settings.vram_gib,
        "--formal_vram_budget_gb": settings.formal_vram_gib or settings.vram_gib,
    }
    for flag, value in values.items():
        if flag in args:
            args[args.index(flag) + 1] = str(value)
        else:
            args.extend([flag, str(value)])
    return [
        "bash",
        str(settings.infra_checkout / "scripts/launch/run_chain.sh"),
        "--mode",
        "lilab",
        "--workspace",
        str(settings.workspace),
        "--run_name",
        settings.run_name,
        "--data_dir",
        str(settings.data_dir),
        "--no_auto_resume",
        "--healthgate_mode",
        "blocking",
        "--result_authority",
        "diagnostic",
        "--no-data_analysis_enabled",
        "--no-ml_lit_review_enabled",
        *args,
    ]


def credential_status(config: Path) -> dict[str, bool]:
    names = required_workflow_api_keys(
        config, disabled_roles=frozenset({"data_analysis", "lit_review"})
    )
    return {name: bool(os.environ.get(name, "").strip()) for name in sorted(names)}


def require_credentials(config: Path) -> dict[str, bool]:
    """Fail before creating a notebook log or workspace; never echo key values."""
    status = credential_status(config)
    missing = [name for name, present in status.items() if not present]
    if missing:
        raise ValueError(
            "Missing exported keys: "
            + ", ".join(missing)
            + ". Export them from a trusted external secret file before starting this terminal/Jupyter server. "
            "Never paste keys in notebooks, scripts or JSON."
        )
    return status


def inspect(settings: PetExperiment, *, launch: bool = False) -> dict:
    """Preview validates saved inputs; launch also checks exported keys and CUDA."""
    command = build_command(settings)
    revision = verify_framework_pin(ROOT, settings.infra_checkout)
    verify_installed_framework(revision, ROOT)
    strategy = verify_planner_setup(
        settings.llm_config,
        settings.infra_checkout,
        environment=child_environment(settings),
    )
    keys = credential_status(settings.llm_config)
    splits = inspect_data(settings.composition, settings.data_dir, decode=launch)
    fingerprint = composition_identity(settings, str(settings.composition))
    gpu = None
    if launch:
        if os.geteuid() == 0:
            raise ValueError("run this demo as a normal user, not root")
        require_credentials(settings.llm_config)
        settings.workspace.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(settings.workspace.parent, os.W_OK):
            raise ValueError(
                f"Output directory is not writable: {settings.workspace.parent}"
            )
        gpu = verify_gpu(settings)
    return {
        "kind": "pet-teaching-demo",
        "scientific_reproduction": False,
        "settings": settings.model_dump(mode="json"),
        "infra_revision": revision,
        "exp_revision": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "composition_fingerprint": fingerprint,
        "planner_strategy_identity": strategy.model_dump(mode="json"),
        "input_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (settings.llm_config, settings.workflow)
        },
        "split_manifests": {
            role: report.model_dump(mode="json") for role, report in splits.items()
        },
        "api_key_status": keys,
        "gpu": gpu,
        "command": command,
        "inactive": ["data_analysis", "literature_review", "human_advice"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    settings = PetExperiment.model_validate_json(args.experiment.read_text())
    receipt = inspect(settings, launch=args.launch)
    print(json.dumps(receipt, indent=2), flush=True)
    print("Native command: " + shlex.join(receipt["command"]), flush=True)
    if args.dry_run:
        subprocess.run(
            [*receipt["command"], "--dry-run"],
            cwd=settings.infra_checkout,
            env=child_environment(settings),
            check=True,
        )
    if args.launch:
        path = settings.workspace.with_suffix(".tutorial.json")
        with path.open("x") as stream:
            json.dump(receipt, stream, indent=2)
        os.execvpe("bash", receipt["command"], child_environment(settings))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(f"Pet tutorial refused: {error}")
