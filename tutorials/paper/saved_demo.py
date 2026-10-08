"""Save a new TESS/TIDMAD run from its existing JSON, without rebuilding its task."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from tutorials.paper.quick_demo import DemoFiles
from tutorials.paper.result_identity import read_settings
from tutorials.paper.runner import ROOT, disjoint

SavedTask = Literal["tess", "tidmad"]


def _files(project: Path, task: SavedTask, name: str) -> DemoFiles:
    if task not in ("tess", "tidmad"):
        raise ValueError("saved-demo editing supports tess or tidmad")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}", name):
        raise ValueError("use a short filename-safe demo name")
    project = project.resolve()
    run_name = f"{task}_{name}"
    return DemoFiles(
        task=task,
        experiment=project / "experiments" / f"{run_name}.json",
        script=project / "scripts" / f"run-{run_name}.sh",
        workspace=project / "runs" / run_name,
        log=project / "runs" / f"{run_name}.console.log",
        completion=project / "runs" / f"{run_name}.notebook-run.json",
    )


def load_demo(project: Path, task: SavedTask, *, name: str) -> DemoFiles:
    """Select a saved pair without creating inputs, tasks or results."""
    from tutorials.shared.saved_script import validate_launcher

    files = _files(project, task, name)
    settings = read_settings(files.experiment, task)
    if (
        settings.workspace != files.workspace
        or settings.run_name != files.workspace.name
    ):
        raise ValueError("saved JSON must retain this named demo's run identity")
    if any(not disjoint(project, p) for p in (ROOT, settings.infra_checkout)):
        raise ValueError("use an external project separate from both checkouts")
    module = (
        "tutorials.paper.tidmad.runner"
        if task == "tidmad"
        else "tutorials.paper.runner"
    )
    validate_launcher(
        files.experiment, files.script, checkout=ROOT, runner_module=module
    )
    return files


def save_variant(
    project: Path, source: DemoFiles, *, name: str, changes: dict
) -> DemoFiles:
    """Clone validated saved values into a fresh JSON/script/workspace identity.

    The existing task and routing stay bound by reference. This saves files only;
    native review/launch still owns scientific and hardware admission.
    """
    if source.task not in ("tess", "tidmad"):
        raise ValueError("saved-demo editing supports tess or tidmad")
    if source.experiment.parent.resolve() != (project / "experiments").resolve():
        raise ValueError("select a saved experiment inside this external project")
    prefix = f"{source.task}_"
    if not source.experiment.stem.startswith(prefix):
        raise ValueError("select a named quick-demo experiment")
    selected = load_demo(
        project, source.task, name=source.experiment.stem.removeprefix(prefix)
    )
    if selected != source:
        raise ValueError("selected demo paths disagree with its saved pair")
    if {"workspace", "run_name"} & changes.keys():
        raise ValueError("use name to choose a fresh run identity")
    original = read_settings(source.experiment, source.task)
    files = _files(project, source.task, name)
    values = original.model_dump() | changes
    values.update(workspace=files.workspace, run_name=files.workspace.name)
    settings = type(original).model_validate(values)
    destinations = (
        files.experiment,
        files.script,
        files.workspace,
        files.log,
        files.completion,
        files.workspace.with_name(files.workspace.name + ".tutorial.json"),
    )
    if any(path.exists() or path.is_symlink() for path in destinations):
        raise ValueError(
            "choose a fresh demo name; existing inputs and results are retained"
        )
    for path in (files.experiment, files.script, files.workspace):
        if any(
            not disjoint(path, root)
            for root in (ROOT, settings.infra_checkout, settings.data_dir)
        ):
            raise ValueError(
                "saved inputs and workspace must stay separate from data and checkouts"
            )
    if source.task == "tidmad":
        from tutorials.paper.tidmad.project import write_launcher
    else:
        from tutorials.paper.project import write_launcher
    # Both writers use exclusive creation; no prior file is overwritten.
    with files.experiment.open("x") as stream:
        stream.write(settings.model_dump_json(indent=2))
    write_launcher(files.script, files.experiment, settings.infra_checkout)
    return files
