"""Initialize TIDMAD inputs in a fresh user-owned project."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
from pathlib import Path

import yaml

from tasks.tidmad.runtime.file_split import FileSplit
from tutorials.paper.planner_setup import copy_llm_config
from tutorials.paper.preflight import shell_setup_guard
from tutorials.paper.runner import ROOT, disjoint
from tutorials.paper.tidmad.runner import TidmadExperiment


def write_launcher(
    destination: Path, experiment: Path, infra: Path, *, final: bool = False
):
    for path in (destination, experiment):
        if any(not disjoint(path, repo) for repo in (ROOT, infra)):
            raise ValueError("write only in the external project")
    module = "final_test" if final else "runner"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x") as stream:
        stream.write(
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            f"EXP_CHECKOUT={shlex.quote(str(ROOT))}\nEXPERIMENT={shlex.quote(str(experiment))}\n"
            + shell_setup_guard()
            + 'cd "$EXP_CHECKOUT"\n'
            f'exec "$EXP_CHECKOUT/.venv/bin/python" -B -m tutorials.paper.tidmad.{module} --experiment "$EXPERIMENT" "$@"\n'
        )
    destination.chmod(0o755)


def write_file_split_task(task: Path, split: FileSplit) -> Path:
    if task.resolve().is_relative_to(ROOT):
        raise ValueError("edit a user-owned task copy")
    source = task / "compositions/continuous_regression.yaml"
    target = task / "compositions/file_holdout.yaml"
    declaration = yaml.safe_load(source.read_text())
    declaration["task_data_path"] = {
        "file": "../runtime/file_split.py",
        "symbol": "FileSplitDataPath",
        "id": "tidmad_file_split",
        "config": {"split": split.model_dump(mode="json")},
    }
    with target.open("x") as stream:
        yaml.safe_dump(declaration, stream, sort_keys=False)
    return target


def create_project(project: Path, infra: Path):
    project, infra = project.resolve(), infra.resolve()
    if any(not disjoint(project, repo) for repo in (ROOT, infra)) or project.exists():
        raise ValueError("choose a fresh project outside both source checkouts")
    project.mkdir(parents=True)
    shutil.copytree(
        ROOT / "tasks/tidmad",
        project / "tasks/tidmad",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for name in (
        "notebooks",
        "experiments",
        "llm",
        "scripts",
        "data/band-0-3",
        "runs",
        "advice",
        "final-test",
    ):
        (project / name).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        ROOT / "tutorials/paper/notebooks/02_tidmad_tutorial.ipynb",
        project / "notebooks/02_tidmad_tutorial.ipynb",
    )
    copy_llm_config(
        ROOT / "experiments/tidmad/main_fixed_workflow/iclr_official_v1.json",
        project / "llm/agents.json",
    )
    shutil.copyfile(
        ROOT / "tasks/tidmad/reference_data/segment_anchors.json",
        project / "data/band-0-3/segment_anchors.json",
    )
    (project / "advice/README.txt").write_text(
        "This NoPrior entrypoint disables human advice and data analysis. Literature review remains enabled. No advice file is consumed.\n"
    )
    settings = TidmadExperiment(
        infra_checkout=infra,
        data_dir=project / "data/band-0-3",
        workspace=project / "runs/paper-pool-001",
        run_name="tidmad_pool_001",
        gpu=None,
        trial_train_fraction=0.5,
        trial_val_fraction=0.1,
        composition=project
        / "tasks/tidmad/compositions/continuous_regression_frozen_pool.yaml",
        llm_config=project / "llm/agents.json",
    )
    experiment = project / "experiments/tidmad-experiment.json"
    experiment.write_text(settings.model_dump_json(indent=2))
    write_launcher(project / "scripts/run-tidmad.sh", experiment, infra)
    (project / "project.json").write_text(
        json.dumps(
            {
                "exp_checkout": str(ROOT),
                "infra_checkout": str(infra),
                "default_experiment": str(experiment),
            },
            indent=2,
        )
    )
    print(
        f"Created {project}. Stage only training/validation 0000–0003 in data/band-0-3."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--infra-checkout", type=Path, required=True)
    args = parser.parse_args()
    create_project(args.project, args.infra_checkout)


if __name__ == "__main__":
    main()
