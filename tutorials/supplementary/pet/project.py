"""Initialize one editable external Pet project, without copying image data."""

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
from tutorials.supplementary.pet.settings import PetExperiment

TEMPLATES = ROOT / "experiments/oxford_iiit_pet/tutorial_demo"


def write_launcher(destination: Path, experiment: Path) -> None:
    saved_script.write_launcher(
        destination,
        experiment,
        checkout=ROOT,
        runner_module="tutorials.supplementary.pet.runner",
    )


def validate_launcher(experiment: Path, script: Path) -> None:
    """Check the selected saved-file bindings before review or delegation."""
    saved_script.validate_launcher(
        experiment,
        script,
        checkout=ROOT,
        runner_module="tutorials.supplementary.pet.runner",
    )


def save_variant(
    project: Path, source: Path, *, name: str, changes: dict
) -> tuple[Path, Path]:
    """Save a new external JSON/script pair without replacing an earlier experiment."""
    project, source = project.resolve(), source.resolve()
    settings = PetExperiment.model_validate_json(source.read_text())
    if source.parent != project / "experiments" or any(
        not disjoint(project, path)
        for path in (ROOT, settings.infra_checkout, settings.data_dir)
    ):
        raise ValueError("save variants inside your initialized external project")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}", name):
        raise ValueError("choose a short filename-safe variant name")
    experiment = project / "experiments" / f"{name}.json"
    script = project / "scripts" / f"run-{name}.sh"
    changed = PetExperiment.model_validate(
        {
            **settings.model_dump(),
            **changes,
            "run_name": name,
            "workspace": project / "runs" / name,
        }
    )
    if any(p.exists() for p in (experiment, script, changed.workspace)):
        raise ValueError(
            "choose a new variant name; existing files and results are never overwritten"
        )
    with experiment.open("x") as stream:
        stream.write(changed.model_dump_json(indent=2) + "\n")
    write_launcher(script, experiment)
    return experiment, script


def create_project(project: Path, infra: Path, images: Path) -> Path:
    project, infra, images = project.resolve(), infra.resolve(), images.resolve()
    if any(not disjoint(project, p) for p in (ROOT, infra, images)):
        raise ValueError(
            "new project must be separate from both repositories and the image directory"
        )
    if project.exists():
        raise ValueError(
            "choose a new project directory; existing projects are never overwritten"
        )
    settings = PetExperiment(
        infra_checkout=infra,
        data_dir=images,
        workspace=project / "runs/pet_demo_001",
        composition=project / "tasks/pet/compositions/bounded_qualification.yaml",
        llm_config=project / "llm/agents.json",
        workflow=project / "experiments/workflow.json",
    )
    notebook = ROOT / "tutorials/supplementary/pet/pet_tutorial.ipynb"
    if not notebook.is_file():
        raise ValueError(
            "Pet notebook template is missing; restore the exp checkout before initializing"
        )
    project.mkdir(parents=True)
    for name in (
        "tasks",
        "llm",
        "experiments",
        "scripts",
        "notebooks",
        "runs",
        "plots",
        "data",
    ):
        (project / name).mkdir()
    shutil.copytree(
        ROOT / "tasks/oxford_iiit_pet",
        project / "tasks/pet",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    write_test_llm_config(project / "llm/agents.json")
    shutil.copyfile(TEMPLATES / "workflow.json", project / "experiments/workflow.json")
    # Keep the repository gallery visible, but never seed a user's notebook
    # with old scores that could survive an interrupted Run All.
    notebook_data = json.loads(notebook.read_text())
    for cell in notebook_data["cells"]:
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    (project / "notebooks/pet_tutorial.ipynb").write_text(
        json.dumps(notebook_data, indent=1) + "\n"
    )
    experiment = project / "experiments/pet-demo.json"
    experiment.write_text(settings.model_dump_json(indent=2) + "\n")
    write_launcher(project / "scripts/run-pet.sh", experiment)
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
    (project / "data/images.json").write_text(
        json.dumps(
            {"images": str(images), "copied": False, "authority": str(experiment)},
            indent=2,
        )
    )
    return experiment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--infra-checkout", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    args = parser.parse_args()
    experiment = create_project(args.project, args.infra_checkout, args.images)
    print(
        f"Saved experiment: {experiment}\nPreview: bash {shlex.quote(str(args.project.resolve() / 'scripts/run-pet.sh'))}"
    )


if __name__ == "__main__":
    main()
