"""Save external Project8/LIGO notebooks, configurations and launch scripts."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
from pathlib import Path

from tutorials.paper.preflight import shell_setup_guard
from tutorials.paper.prepared.data import Task
from tutorials.paper.prepared.runner import PreparedExperiment
from tutorials.paper.runner import ROOT, disjoint
from tutorials.shared.llm_setup import write_test_llm_config


def write_launcher(destination: Path, experiment: Path, infra: Path):
    if any(
        not disjoint(path, repo)
        for path in (destination, experiment)
        for repo in (ROOT, infra)
    ):
        raise ValueError("write only in an external user project")
    with destination.open("x") as stream:
        stream.write(
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            f"EXP_CHECKOUT={shlex.quote(str(ROOT))}\nEXPERIMENT={shlex.quote(str(experiment.resolve()))}\n"
            + shell_setup_guard()
            + 'cd "$EXP_CHECKOUT"\n'
            'exec "$EXP_CHECKOUT/.venv/bin/python" -B -m tutorials.paper.prepared.runner --experiment "$EXPERIMENT" "$@"\n'
        )
    destination.chmod(0o755)


def create_project(project: Path, infra: Path, task: Task):
    project, infra = project.resolve(), infra.resolve()
    if project.exists() or any(not disjoint(project, p) for p in (ROOT, infra)):
        raise ValueError("choose a new external project directory")
    for name in (
        "notebooks",
        "experiments",
        "llm",
        "advice",
        "scripts",
        "data",
        "tasks",
        "runs",
        "plots",
    ):
        (project / name).mkdir(parents=True)
    shutil.copytree(
        ROOT / "tasks/shared",
        project / "tasks/shared",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    notebook = (
        "03_project8_tutorial.ipynb" if task == "project8" else "04_ligo_tutorial.ipynb"
    )
    shutil.copyfile(
        ROOT / "tutorials/paper/notebooks" / notebook, project / "notebooks" / notebook
    )
    variant = (
        "main_fixed_workflow_dual_representation"
        if task == "project8"
        else "main_fixed_workflow"
    )
    experiment = ROOT / f"experiments/phyts_{task}" / variant
    write_test_llm_config(project / "llm/agents.json")
    shutil.copyfile(
        experiment / "literature_review.yaml", project / "llm/literature_review.yaml"
    )
    (project / "advice/README.txt").write_text(
        "Human advice and Data Analysis are disabled. No advice file is read. Literature Review remains enabled.\n"
    )
    settings = PreparedExperiment(
        task=task,
        infra_checkout=infra,
        data_dir=project / "data/demo-001",
        workspace=project / "runs/initial-001",
        run_name=f"{task}_initial_001",
        gpu=None,
        iterations=3,
        epochs=4,
        trial_train_fraction=0.5,
        trial_val_fraction=0.5,
        composition=project / f"tasks/{task}-demo-001/compositions/regression.yaml",
        llm_config=project / "llm/agents.json",
        literature_config=project / "llm/literature_review.yaml",
    )
    config = project / f"experiments/{task}-experiment.json"
    config.write_text(settings.model_dump_json(indent=2))
    write_launcher(project / f"scripts/run-{task}.sh", config, infra)
    (project / "project.json").write_text(
        json.dumps(
            {
                "exp_checkout": str(ROOT),
                "infra_checkout": str(infra),
                "default_experiment": str(config),
                "task": task,
            },
            indent=2,
        )
    )
    print(f"Created {project}. Next prepare demo-001 data before opening the notebook.")


def prepare_demo(project: Path, task: Task, *, name: str, settings: dict):
    from tutorials.paper.quick_demo import DemoFiles

    project = project.resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}", name):
        raise ValueError("choose a short filename-safe DEMO_NAME")
    initial = PreparedExperiment.model_validate_json(
        (project / f"experiments/{task}-experiment.json").read_text()
    )
    if initial.task != task or any(
        not disjoint(project, p) for p in (ROOT, initial.infra_checkout)
    ):
        raise ValueError("use the matching external project")
    values = initial.model_dump()
    values.update(
        settings,
        run_name=f"{task}_{name}",
        workspace=project / "runs" / f"{task}_{name}",
    )
    updated = PreparedExperiment.model_validate(values)
    path = project / f"experiments/{task}_{name}.json"
    text = updated.model_dump_json(indent=2)
    if path.exists() and path.read_text() != text:
        raise ValueError("choose a new DEMO_NAME for changed settings")
    if not path.exists():
        with path.open("x") as stream:
            stream.write(text)
    script = project / f"scripts/run-{task}_{name}.sh"
    if not script.exists():
        write_launcher(script, path, updated.infra_checkout)
    return DemoFiles(
        task=task,
        experiment=path,
        script=script,
        workspace=updated.workspace,
        log=project / f"runs/{task}_{name}.console.log",
        completion=project / f"runs/{task}_{name}.notebook-run.json",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--infra-checkout", type=Path, required=True)
    parser.add_argument("--task", choices=("project8", "ligo"), required=True)
    args = parser.parse_args()
    create_project(args.project, args.infra_checkout, args.task)


if __name__ == "__main__":
    main()
