"""Review saved Cancer inputs, delegate to their script and plot recorded evidence."""

from __future__ import annotations

import hashlib
import shlex
import subprocess
from pathlib import Path

import yaml

from tutorials.shared.progress import plot_progress, read_progress
from tutorials.shared.runtime import ROOT, disjoint
from tutorials.shared.saved_run import run_saved_script
from tutorials.supplementary.cancer.data import verify_files
from tutorials.supplementary.cancer.project import validate_launcher
from tutorials.supplementary.cancer.settings import CancerExperiment


def input_digest(experiment: Path, script: Path) -> str:
    """Bind the standard copied package and saved launch inputs, not dataset bytes."""
    settings = CancerExperiment.model_validate_json(experiment.read_text())
    verify_files(settings)
    files = [
        experiment,
        script,
        settings.llm_config,
        settings.workflow,
    ]
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
    raw = settings.data_dir / "cpdb/data.h5"
    stat = raw.stat()
    digest.update(f"{raw.resolve()}:{stat.st_size}:{stat.st_mtime_ns}".encode())
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
    settings = CancerExperiment.model_validate_json(experiment.read_text())
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

The one CPDB file has the expected size and disjoint original masks: {data["original_masks"]}. **SHA-256 has not been freshly checked by this review.** Launch checks its official SHA-256 before training.

Inspect the composition above, its `declared/tutorial_source_files.json`, `llm_config`, `workflow` and this script before launch. The original graph and supplied Train/Validation/Test masks are unchanged. Fractions select active labels, not smaller graphs. **Validation supplies search feedback. Test labels are not loaded or used.**

Data Analysis, literature review and human advice are disabled. The task explicitly declares no Health checks; successful execution does not mean Health PASS. Runtime and scoreability checks still apply.

{launch}

Outputs: `{settings.workspace}`; native launch receipt `.tutorial.json`, notebook log `.console.log` and completion `.notebook-run.json` are siblings of that directory. A direct script launch prints to its terminal. Neither time allowances nor the notebook timeout are a whole-run billing/GPU cap.
"""


def run_demo(experiment: Path, script: Path, *, timeout_seconds: float = 3600) -> dict:
    """Saved script owns execution; shared helper owns cache and process cleanup."""
    from tutorials.supplementary.cancer.runner import require_credentials

    settings = CancerExperiment.model_validate_json(experiment.read_text())
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
    settings = CancerExperiment.model_validate_json(experiment.read_text())
    if not disjoint(output, settings.infra_checkout) or not disjoint(
        output, settings.data_dir
    ):
        raise ValueError(
            "plot output must be outside the framework checkout and raw data"
        )
    declaration = yaml.safe_load(settings.composition.read_text())
    if declaration.get("task_health") != {"none": True}:
        raise ValueError(
            "Cancer plotting requires the selected task's explicit no-Health declaration"
        )
    points = read_progress(settings.workspace, health_policy="none")
    scored = [p for p in points if p.score is not None]
    if not scored:
        raise ValueError(
            "No measured Formal score yet. Inspect native records; no zero or substitute score was invented."
        )
    if any(p.metric != "mean_auprc" or p.direction != "higher" for p in scored):
        raise ValueError("selected records are not Cancer mean_auprc (higher)")
    return plot_progress(
        settings.workspace,
        output,
        title="Cancer CPDB (no Health checks)",
        expected_iterations=settings.iterations,
        health_policy="none",
    )
