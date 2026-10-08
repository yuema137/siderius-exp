"""Initialize an external SuperNEMO project and save new experiment/script pairs."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
from pathlib import Path

from tutorials.shared import saved_script
from tutorials.shared.llm_setup import write_test_llm_config
from tutorials.shared.runtime import ROOT, disjoint
from tutorials.supplementary.supernemo.prepare import require_external_output
from tutorials.supplementary.supernemo.settings import SuperNemoExperiment

RUNNER = "tutorials.supplementary.supernemo.runner"


def write_launcher(destination: Path, experiment: Path) -> None:
    saved_script.write_launcher(
        destination, experiment, checkout=ROOT, runner_module=RUNNER
    )


def validate_launcher(experiment: Path, script: Path) -> None:
    saved_script.validate_launcher(
        experiment, script, checkout=ROOT, runner_module=RUNNER
    )


def save_variant(
    project: Path, source: Path, *, name: str, changes: dict
) -> tuple[Path, Path]:
    """Validate edits and save a fresh pair; never mutate an earlier run's inputs."""
    project, source = project.resolve(), source.resolve()
    settings = SuperNemoExperiment.model_validate_json(source.read_text())
    if source.parent != project / "experiments" or any(
        not disjoint(project, path)
        for path in (ROOT, settings.infra_checkout, settings.data_dir)
    ):
        raise ValueError("save variants inside your initialized external project")
    require_external_output(project, settings.data_dir)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}", name):
        raise ValueError("choose a short filename-safe variant name")
    changed = SuperNemoExperiment.model_validate(
        {
            **settings.model_dump(),
            **changes,
            "run_name": name,
            "workspace": project / "runs" / name,
        }
    )
    experiment = project / "experiments" / f"{name}.json"
    script = project / "scripts" / f"run-{name}.sh"
    if any(path.exists() for path in (experiment, script, changed.workspace)):
        raise ValueError(
            "choose a new variant name; existing inputs/results are never overwritten"
        )
    with experiment.open("x") as stream:
        stream.write(changed.model_dump_json(indent=2) + "\n")
    write_launcher(script, experiment)
    return experiment, script


def create_project(project: Path, infra: Path, data: Path) -> Path:
    project, infra, data = project.resolve(), infra.resolve(), data.resolve()
    if any(not disjoint(project, path) for path in (ROOT, infra, data)):
        raise ValueError(
            "new project must be separate from source checkouts and raw data"
        )
    require_external_output(project, data)
    if project.exists():
        raise ValueError(
            "choose a new project directory; existing projects are never overwritten"
        )
    notebook = ROOT / "tutorials/supplementary/supernemo/supernemo_tutorial.ipynb"
    if not notebook.is_file():
        raise ValueError(
            "SuperNEMO notebook template is missing; restore the exp checkout"
        )
    settings = SuperNemoExperiment(
        infra_checkout=infra,
        data_dir=data,
        workspace=project / "runs/supernemo_demo_001",
        composition=project / "tasks/supernemo/compositions/signal_background.yaml",
        llm_config=project / "llm/agents.json",
        workflow=project / "experiments/workflow.json",
    )
    for name in (
        "tasks",
        "llm",
        "experiments",
        "scripts",
        "notebooks",
        "runs",
        "plots",
    ):
        (project / name).mkdir(parents=True)
    shutil.copytree(
        ROOT / "tasks/supernemo_signal_background",
        project / "tasks/supernemo",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    write_test_llm_config(settings.llm_config)
    shutil.copyfile(
        ROOT / "experiments/supernemo_signal_background/tutorial_demo/workflow.json",
        settings.workflow,
    )
    content = json.loads(notebook.read_text())
    for cell in content["cells"]:
        if cell["cell_type"] == "code":
            cell["outputs"], cell["execution_count"] = [], None
    (project / "notebooks/supernemo_tutorial.ipynb").write_text(
        json.dumps(content, indent=1) + "\n"
    )
    experiment = project / "experiments/supernemo-demo.json"
    experiment.write_text(settings.model_dump_json(indent=2) + "\n")
    write_launcher(project / "scripts/run-supernemo.sh", experiment)
    (project / "project.json").write_text(
        json.dumps(
            {
                "exp_checkout": str(ROOT),
                "infra_checkout": str(infra),
                "default_experiment": str(experiment),
                "data_copied": False,
            },
            indent=2,
        )
        + "\n"
    )
    return experiment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--infra-checkout", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    experiment = create_project(args.project, args.infra_checkout, args.data_dir)
    print(
        f"Saved experiment: {experiment}\nPreview: bash {shlex.quote(str(args.project.resolve() / 'scripts/run-supernemo.sh'))}"
    )


if __name__ == "__main__":
    main()
