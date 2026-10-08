"""Preview or execute the saved Cancer experiment through the native chain."""

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
from tutorials.supplementary.cancer.data import selected_task, verify_files
from tutorials.supplementary.cancer.settings import CancerExperiment


def validate_locations(settings: CancerExperiment) -> None:
    inputs = (settings.composition, settings.llm_config, settings.workflow)
    for path in (*inputs, settings.workspace, settings.data_dir):
        if any(not disjoint(path, repo) for repo in (ROOT, settings.infra_checkout)):
            raise ValueError(
                "data, editable inputs and outputs must be outside both source checkouts"
            )
    if not disjoint(settings.workspace, settings.data_dir):
        raise ValueError("run workspace must be separate from raw data")
    if settings.workspace.exists():
        raise ValueError(
            "run workspace already exists; keep its records and select a fresh name/path"
        )
    for path in inputs:
        if not path.is_file():
            raise ValueError(
                f"Missing saved input: {path}. Restore your external project file."
            )
        if not disjoint(path, settings.workspace) or not disjoint(
            path, settings.data_dir
        ):
            raise ValueError(
                "saved inputs must be outside data and run output directories"
            )


def build_command(settings: CancerExperiment) -> list[str]:
    validate_locations(settings)
    args = render_siderius_args(
        settings.workflow,
        repository_root=settings.workflow.parent.parent,
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
        "--trial_portion": 1.0,
        "--eval_portion": settings.trial_eval_label_fraction,
        "--formal_portion": 1.0,
        "--formal_eval_portion": settings.formal_eval_label_fraction,
        "--train_portion": settings.trial_train_label_fraction,
        "--formal_train_portion": settings.formal_train_label_fraction,
        "--trial_time_budget_minutes": settings.trial_minutes,
        "--formal_time_budget_minutes": settings.formal_minutes,
        "--trial_vram_budget_gb": settings.trial_vram_gib or settings.vram_gib,
        "--formal_vram_budget_gb": settings.formal_vram_gib or settings.vram_gib,
        "--plan_overrides": json.dumps(
            {
                "is_trial": True,
                "trial_strategy": "snapshot",
                "eval_strategy": "snapshot",
            }
        ),
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
    status = credential_status(config)
    missing = [name for name, present in status.items() if not present]
    if missing:
        raise ValueError(
            "Missing exported keys: "
            + ", ".join(missing)
            + ". Export them from a trusted external secret file before starting Jupyter/this terminal; never paste values in notebooks or JSON."
        )
    return status


def inspect(settings: CancerExperiment, *, launch: bool = False) -> dict:
    """Offline preview; launch additionally checks keys, CUDA and the official CPDB SHA-256."""
    command = build_command(settings)
    revision = verify_framework_pin(ROOT, settings.infra_checkout)
    verify_installed_framework(revision, ROOT)
    strategy = verify_planner_setup(
        settings.llm_config,
        settings.infra_checkout,
        environment=child_environment(settings),
    )
    selected_task(settings)
    fingerprint = composition_identity(settings, str(settings.composition))
    keys = credential_status(settings.llm_config)
    gpu = None
    if launch:
        if os.geteuid() == 0:
            raise ValueError("run this demo as a normal user, not root")
        require_credentials(settings.llm_config)
        gpu = verify_gpu(settings)
    data = verify_files(settings, hashes=launch)
    return {
        "kind": "cancer-teaching-demo",
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
            for p in (settings.workflow, settings.llm_config)
        },
        "data": data,
        "api_key_status": keys,
        "gpu": gpu,
        "command": command,
        "inactive": [
            "data_analysis",
            "literature_review",
            "human_advice",
            "task_health",
        ],
        "evaluation_role": "Fixed validation split used for agent search; final test split remains unused",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    settings = CancerExperiment.model_validate_json(args.experiment.read_text())
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
        settings.workspace.parent.mkdir(parents=True, exist_ok=True)
        with settings.workspace.with_suffix(".tutorial.json").open("x") as stream:
            json.dump(receipt, stream, indent=2)
        os.execvpe("bash", receipt["command"], child_environment(settings))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(f"Cancer tutorial refused: {error}")
