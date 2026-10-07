"""Create user-owned tutorial inputs outside both source checkouts."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
from pathlib import Path

from tutorials.paper.planner_setup import copy_llm_config
from tutorials.paper.preflight import shell_setup_guard
from tutorials.paper.runner import ROOT, TutorialExperiment, disjoint


def write_launcher(destination: Path, experiment: Path, infra: Path) -> None:
    """Generate an editable external shell entrypoint with explicit source binding."""
    for path in (destination, experiment):
        if any(not disjoint(path, repo) for repo in (ROOT, infra)):
            raise ValueError(
                "user scripts and experiments must be outside both source checkouts"
            )
    source = (
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        "# User-owned entrypoint. Edit EXPERIMENT to select a saved experiment.\n"
        f"EXP_CHECKOUT={shlex.quote(str(ROOT))}\n"
        f"EXPERIMENT={shlex.quote(str(experiment.resolve()))}\n"
        "# Credentials must already be exported in this terminal.\n"
        + shell_setup_guard()
        + 'cd "$EXP_CHECKOUT"\n'
        'exec "$EXP_CHECKOUT/.venv/bin/python" -B -m tutorials.paper.runner '
        '--experiment "$EXPERIMENT" "$@"\n'
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x") as stream:
        stream.write(source)
    destination.chmod(0o755)


def create_project(project: Path, infra: Path) -> None:
    """Copy editable inputs once; never overwrite a project or source file."""
    project, infra = project.resolve(), infra.resolve()
    if not all(disjoint(project, repo) for repo in (ROOT, infra)):
        raise ValueError("project must be outside and separate from both checkouts")
    if project.exists():
        raise ValueError(
            "choose a new project directory; existing projects are never overwritten"
        )
    project.mkdir(parents=True)
    task = project / "tasks/tess"
    shutil.copytree(
        ROOT / "tasks/phyts_tess",
        task,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for name in (
        "notebooks",
        "experiments",
        "llm",
        "advice",
        "scripts",
        "data",
        "runs",
    ):
        (project / name).mkdir(exist_ok=True)
    shutil.copyfile(
        ROOT / "tutorials/paper/notebooks/01_tess_tutorial.ipynb",
        project / "notebooks/01_tess_tutorial.ipynb",
    )
    copy_llm_config(
        ROOT / "experiments/phyts_tess/main_fixed_workflow/agents.json",
        project / "llm/agents.json",
    )
    shutil.copyfile(
        ROOT / "experiments/phyts_tess/main_fixed_workflow/advice.json",
        project / "advice/human_advice.example.json",
    )
    experiment = TutorialExperiment(
        version="siderius-tess-tutorial-v1",
        infra_checkout=infra,
        data_dir=project / "data/tess-data",
        workspace=project / "runs/tess-demo-001",
        run_name="tess_demo_001",
        trial_train_fraction=1.0,
        trial_val_fraction=1.0,
        gpu="RTX 5090",
        composition=task / "compositions/rotation_regression.yaml",
        llm_config=project / "llm/agents.json",
    )
    path = project / "experiments/tess-experiment.json"
    path.write_text(experiment.model_dump_json(indent=2))
    write_launcher(project / "scripts/run-tess.sh", path, infra)
    (project / "project.json").write_text(
        json.dumps(
            {
                "exp_checkout": str(ROOT),
                "infra_checkout": str(infra),
                "default_experiment": str(path),
            },
            indent=2,
        )
    )
    print(
        f"Created project: {project}\nAdvice example is inactive: this entrypoint is NoPrior."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--infra-checkout", type=Path, required=True)
    args = parser.parse_args()
    create_project(args.project, args.infra_checkout)


if __name__ == "__main__":
    main()
