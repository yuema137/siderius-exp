"""Preview an explicit prepared-task workflow command; never start a clock.

The deployment supervisor owns execution, credentials, deadlines and collection.
Qualification parameters are applied in memory; frozen experiment files are
never edited to shorten a smoke test.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.shared.fixed_workflow_config import render_siderius_args
from experiments.shared.information_treatment import resolve_information_treatment


def build_command(
    *,
    experiment: Path,
    checkout: Path,
    data: Path,
    workspace: Path,
    run_name: str,
    qualification: bool,
) -> list[str]:
    root = Path(__file__).resolve().parents[2]
    experiment = experiment.resolve()
    if not experiment.is_relative_to(root / "experiments"):
        raise ValueError("experiment must belong to this checkout")
    for protected in (root, checkout.resolve(), data.resolve()):
        if workspace.resolve().is_relative_to(protected) or protected.is_relative_to(
            workspace.resolve()
        ):
            raise ValueError("workspace must be separate from source and data")
    treatment = resolve_information_treatment(
        experiment / "information_treatment.yaml",
        repository_root=root,
        adapter="siderius",
    )
    args = render_siderius_args(
        experiment / "workflow.json", repository_root=root, siderius_checkout=checkout
    )
    if qualification:
        args[args.index("--no-runtime_watchdog")] = "--runtime_watchdog"
        for flag, value in {
            "--num_iterations": "2",
            "--max_epochs": "1",
            "--trial_max_epochs": "1",
            "--formal_max_epochs": "1",
            "--trial_time_budget_minutes": "1",
            "--formal_time_budget_minutes": "2",
        }.items():
            args[args.index(flag) + 1] = value
        args.extend(
            (
                "--validation_max_train_samples",
                "128",
                "--validation_max_phase_seconds",
                "60",
            )
        )
    literature = experiment / "literature_review.yaml"
    if not literature.is_file():
        raise ValueError(
            "enabled literature review requires its experiment configuration"
        )
    launcher = checkout.resolve() / "scripts/launch/run_chain.sh"
    if not launcher.is_file():
        raise ValueError("missing native workflow launcher")
    return [
        "bash",
        str(launcher),
        "--mode",
        "lilab",
        "--workspace",
        str(workspace.resolve()),
        "--data_dir",
        str(data.resolve()),
        "--run_name",
        run_name,
        "--result_authority",
        "scientific",
        "--ml_lit_review_config",
        str(literature),
        *treatment.siderius_args(),
        *args,
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--siderius-checkout", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--qualification", action="store_true")
    args = parser.parse_args()
    command = build_command(
        experiment=args.experiment,
        checkout=args.siderius_checkout,
        data=args.data_dir,
        workspace=args.workspace,
        run_name=args.run_name,
        qualification=args.qualification,
    )
    print(
        json.dumps(
            {"command": command, "qualification": args.qualification, "started": False},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
