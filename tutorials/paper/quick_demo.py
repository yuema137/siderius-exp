"""Prepare external demo inputs and delegate execution to the saved shell script."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from tutorials.paper.result_identity import (
    DemoCompletion,
    input_identity,
    read_settings,
)
from tutorials.paper.runner import ROOT, TutorialExperiment, disjoint


class DemoFiles(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    task: Literal["tess", "tidmad", "project8", "ligo"]
    experiment: Path
    script: Path
    workspace: Path
    log: Path
    completion: Path


def prepare_demo(
    project: Path,
    task: Literal["tess", "tidmad", "project8", "ligo"],
    *,
    name: str,
    settings: dict,
) -> DemoFiles:
    """Save a named demo once; changed inputs require a new name, never overwrite."""
    if task in ("project8", "ligo"):
        from tutorials.paper.prepared.project import prepare_demo as prepared_demo

        return prepared_demo(project, task, name=name, settings=settings)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}", name):
        raise ValueError("use a short filename-safe demo name")
    project = project.resolve()
    binding = json.loads((project / "project.json").read_text())
    if any(not disjoint(project, p) for p in (ROOT, Path(binding["infra_checkout"]))):
        raise ValueError("use an external project")
    if task == "tess":
        from tutorials.paper.project import write_launcher

        schema = TutorialExperiment
    elif task == "tidmad":
        from tasks.tidmad.runtime.file_split import FileSplit
        from tutorials.paper.tidmad.project import write_file_split_task, write_launcher
        from tutorials.paper.tidmad.runner import TidmadExperiment

        schema = TidmadExperiment
    else:
        raise ValueError("choose tess or tidmad")
    initial = schema.model_validate_json(
        (project / "experiments" / f"{task}-experiment.json").read_text()
    )
    values = initial.model_dump()
    values.update(settings)
    run_name = f"{task}_{name}"
    values.update(run_name=run_name, workspace=project / "runs" / run_name)
    if task == "tidmad":
        copy = project / "tasks" / f"tidmad-{name}"
        if not copy.exists():
            shutil.copytree(
                initial.composition.parent.parent,
                copy,
                ignore=shutil.ignore_patterns(
                    "*.pyc", "__pycache__", "file_holdout.yaml"
                ),
            )
            write_file_split_task(copy, FileSplit())
        values.update(
            composition=copy / "compositions/file_holdout.yaml", protocol="file-holdout"
        )
    experiment = schema.model_validate(values)
    config = project / "experiments" / f"{run_name}.json"
    text = experiment.model_dump_json(indent=2)
    if config.exists():
        if config.read_text() != text:
            raise ValueError(
                "This demo name already has different saved settings. Choose a new DEMO_NAME; previous inputs/results are retained."
            )
    else:
        with config.open("x") as stream:
            stream.write(text)
    script = project / "scripts" / f"run-{run_name}.sh"
    if not script.exists():
        write_launcher(script, config, experiment.infra_checkout)
    return DemoFiles(
        task=task,
        experiment=config,
        script=script,
        workspace=experiment.workspace,
        log=project / "runs" / f"{run_name}.console.log",
        completion=project / "runs" / f"{run_name}.notebook-run.json",
    )


def run_demo(files: DemoFiles) -> dict:
    """A Run All orchestration step, not a second training implementation.

    Existing completion evidence reuses results. Interrupted/in-progress runs
    require inspection rather than silent retry or process adoption.
    """
    from tutorials.paper.launch_review import launch_review

    recovery = (
        "Nothing was relaunched. Keep the old records and plot them directly using "
        "PLOT_WORKSPACE (TESS/TIDMAD) or PLOT_EXPERIMENT (Project8/LIGO); "
        "choose a new DEMO_NAME for a new run."
    )
    try:
        settings = read_settings(files.experiment, files.task)
    except (OSError, ValueError) as error:
        guidance = (
            recovery
            if files.completion.exists()
            else "No script was launched. Reload Quick A after repairing the saved configuration."
        )
        raise ValueError(
            f"Cannot read the saved experiment {files.experiment} "
            f"({type(error).__name__}). Restore its original JSON or repair its "
            "configuration before using it, including for PLOT_EXPERIMENT. " + guidance
        ) from None
    if settings.workspace.resolve() != files.workspace.resolve():
        raise ValueError("saved experiment and demo workspace disagree; reload Quick A")
    if files.completion.exists():
        try:
            completed = DemoCompletion.model_validate_json(files.completion.read_text())
        except ValueError:
            raise ValueError(
                "Old or invalid completion receipt cannot establish unchanged inputs. "
                + recovery
            ) from None
        if completed.workspace.resolve() != files.workspace.resolve():
            raise ValueError("Completion belongs to a different workspace. " + recovery)
        if not files.workspace.is_dir():
            raise ValueError(
                "Completed workspace is missing; restore it first. " + recovery
            )
        if not completed.inputs_unchanged:
            raise ValueError("Inputs changed during the recorded run. " + recovery)
        try:
            identity = input_identity(
                files.experiment, files.script, settings, task=files.task
            )
        except (OSError, ValueError, subprocess.SubprocessError):
            raise ValueError(
                "Cannot verify the recorded run's local inputs. " + recovery
            ) from None
        if completed.input_sha256 != identity:
            raise ValueError("Saved inputs changed since execution. " + recovery)
        print(f"Reusing recorded run (no API/GPU work): {files.workspace}", flush=True)
        if completed.exit_code != 0:
            print(
                f"Recorded script exit code: {completed.exit_code}. Inspect {completed.log}; "
                "recorded scores remain available for plotting.",
                flush=True,
            )
        return completed.model_dump(mode="json")
    if files.workspace.exists() or files.log.exists():
        raise ValueError(
            f"Unfinished/existing run: inspect {files.log}; choose a new DEMO_NAME after stopping any active run. Nothing was relaunched."
        )
    sha = hashlib.sha256(files.experiment.read_bytes()).hexdigest()
    identity = input_identity(files.experiment, files.script, settings, task=files.task)
    from tutorials.paper.preflight import require_ready

    require_ready(settings, task=files.task)
    # Surface native preflight errors directly in Jupyter before opening a run log.
    # The saved script repeats these checks when invoked on its own.
    if files.task in ("project8", "ligo"):
        from tutorials.paper.prepared.runner import inspect
    elif files.task == "tidmad":
        from tutorials.paper.tidmad.runner import inspect
    else:
        from tutorials.paper.runner import inspect
    inspect(settings, launch=True)
    report = launch_review(files.experiment, files.script, task=files.task)
    if "**STOP" in report:
        raise ValueError(
            "Complete the saved-file/data checklist above before running the demo."
        )
    if identity != input_identity(
        files.experiment, files.script, settings, task=files.task
    ):
        raise ValueError("Inputs changed during launch checks. " + recovery)
    started = time.monotonic()
    files.log.parent.mkdir(parents=True, exist_ok=True)
    # Native launcher repeats source/data/GPU/credential checks before effects.
    with files.log.open("x") as log:
        process = subprocess.Popen(
            ["bash", str(files.script), "--launch"],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        print(
            f"Started saved script: {files.script}\nLive log: {files.log}", flush=True
        )
        try:
            while True:
                try:
                    code = process.wait(timeout=30)
                    break
                except subprocess.TimeoutExpired:
                    print(
                        f"Search running: {(time.monotonic() - started) / 60:.1f} min; see {files.log.name}",
                        flush=True,
                    )
        except BaseException:
            import signal

            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
    try:
        unchanged = identity == input_identity(
            files.experiment, files.script, settings, task=files.task
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        unchanged = False
    completed = DemoCompletion(
        input_sha256=identity,
        experiment_sha256=sha,
        inputs_unchanged=unchanged,
        exit_code=code,
        elapsed_seconds=time.monotonic() - started,
        workspace=files.workspace,
        log=files.log,
    )
    result = completed.model_dump(mode="json")
    with files.completion.open("x") as stream:
        stream.write(completed.model_dump_json(indent=2))
    if not unchanged:
        print(
            "Inputs changed or became unavailable during execution; this receipt "
            "cannot be reused. Keep the recorded scores for direct plotting.",
            flush=True,
        )
    print(f"Search exit code: {code}. Evidence: {files.completion}", flush=True)
    if code != 0:
        print(
            "The native search returned a nonzero code. Inspect the log to distinguish model rejection from a setup/runtime failure. Recorded results can still be plotted; this workflow demo does not require Health PASS.",
            flush=True,
        )
    return result
