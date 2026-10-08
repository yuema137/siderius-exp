"""Review saved SuperNEMO inputs, delegate to their script and plot recorded evidence."""

from __future__ import annotations

import hashlib
import shlex
import subprocess
from pathlib import Path

import yaml

from tutorials.shared.progress import plot_progress, read_progress
from tutorials.shared.runtime import ROOT, disjoint
from tutorials.shared.saved_run import run_saved_script
from tutorials.supplementary.supernemo.data import verify_files
from tutorials.supplementary.supernemo.prepare import (
    RECEIPT,
    generated_paths,
    verify_prepared,
)
from tutorials.supplementary.supernemo.project import validate_launcher
from tutorials.supplementary.supernemo.settings import SuperNemoExperiment


def input_digest(experiment: Path, script: Path) -> str:
    """Bind the standard copied package and saved launch inputs, not dataset bytes."""
    settings = SuperNemoExperiment.model_validate_json(experiment.read_text())
    verify_prepared(settings.data_dir)
    files = [
        experiment,
        script,
        settings.llm_config,
        settings.workflow,
        settings.data_dir / RECEIPT,
    ]
    files.extend(generated_paths(settings.data_dir))
    files.extend(
        p
        for p in settings.composition.parent.parent.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )
    digest = hashlib.sha256()
    for path in sorted(set(files)):
        digest.update(
            str(path.absolute()).encode()
            + b"\0"
            + str(path.resolve()).encode()
            + b"\0"
            + path.read_bytes()
            + b"\0"
        )
    for checkout in (ROOT, settings.infra_checkout):
        digest.update(str(checkout.resolve()).encode() + b"\0")
        for arguments in (
            ["rev-parse", "HEAD"],
            ["diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--"],
        ):
            digest.update(
                subprocess.check_output(["git", "-C", str(checkout), *arguments])
            )
    return digest.hexdigest()


def review(experiment: Path, script: Path) -> str:
    settings = SuperNemoExperiment.model_validate_json(experiment.read_text())
    validate_launcher(experiment, script)
    data = verify_files(settings)
    rows = "\n".join(
        f"| `{key}` | `{value}` |"
        for key, value in settings.model_dump(mode="json").items()
    )
    command = shlex.join(["bash", str(script)])
    launch = (
        "The output workspace exists. Keep its records; plot it separately or save a fresh variant."
        if settings.workspace.exists()
        else f"Preview (offline):\n```bash\n{command}\n```\nLaunch (API/GPU effects):\n```bash\n{command} --launch\n```"
    )
    return f"""Saved experiment: `{experiment}`. Saved script: `{script}`.

| Setting | Saved value |
|---|---|
{rows}

All {data["source_files"]} official source files and their prepared indexes match recorded bindings and index hashes. **Raw MD5 has not been freshly checked by this review.** Launch repeats every raw MD5 before training.

Inspect the composition above, its `declared/source_files.json`, `llm_config`, `workflow` and this script before launch. The original event-level 80/10/10 split is unchanged. **Validation supplies search feedback. Final test events are not used.**

Data Analysis, literature review and human advice are disabled. The task explicitly declares no Health checks; successful execution does not mean Health PASS. Runtime and scoreability checks still apply.

{launch}

Outputs: `{settings.workspace}`; native launch receipt `.tutorial.json`, notebook log `.console.log` and completion `.notebook-run.json` are siblings of that directory. A direct script launch prints to its terminal. Neither time allowances nor the notebook timeout are a whole-run billing/GPU cap.
"""


def run_demo(experiment: Path, script: Path, *, timeout_seconds: float = 3600) -> dict:
    """Saved script owns execution; shared helper owns cache and process cleanup."""
    from tutorials.supplementary.supernemo.runner import require_credentials

    settings = SuperNemoExperiment.model_validate_json(experiment.read_text())
    validate_launcher(experiment, script)
    return run_saved_script(
        script=script,
        workspace=settings.workspace,
        digest=input_digest(experiment, script),
        ready=lambda: require_credentials(settings.llm_config),
        timeout_seconds=timeout_seconds,
    )


def plot_results(experiment: Path, output: Path):
    """Plot an existing run independently of launch state, data, keys or GPU."""
    settings = SuperNemoExperiment.model_validate_json(experiment.read_text())
    if not disjoint(output, settings.infra_checkout) or not disjoint(
        output, settings.data_dir
    ):
        raise ValueError(
            "plot output must be outside the framework checkout and raw data"
        )
    declaration = yaml.safe_load(settings.composition.read_text())
    if declaration.get("task_health") != {"none": True}:
        raise ValueError(
            "SuperNEMO plotting requires the selected task's explicit no-Health declaration"
        )
    points = read_progress(settings.workspace, health_policy="none")
    scored = [p for p in points if p.score is not None]
    if not scored:
        raise ValueError(
            "No measured Formal score yet. Inspect native records; no zero or substitute score was invented."
        )
    if any(
        p.metric != "energy_matched_roc_auc" or p.direction != "higher" for p in scored
    ):
        raise ValueError(
            "selected records are not SuperNEMO energy_matched_roc_auc (higher)"
        )
    return plot_progress(
        settings.workspace,
        output,
        title="SuperNEMO signal-background (no Health checks)",
        expected_iterations=settings.iterations,
        health_policy="none",
    )
