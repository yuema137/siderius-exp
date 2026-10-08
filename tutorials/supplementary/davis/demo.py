"""Review saved Davis inputs, delegate to their script and plot recorded evidence."""

from __future__ import annotations

import hashlib
import shlex
import subprocess
from pathlib import Path

from tutorials.shared.progress import plot_progress, read_progress
from tutorials.shared.runtime import ROOT, disjoint
from tutorials.shared.saved_run import run_saved_script
from tutorials.supplementary.davis.data import frame_files, verify_files
from tutorials.supplementary.davis.project import validate_launcher
from tutorials.supplementary.davis.settings import DavisExperiment


def input_digest(experiment: Path, script: Path) -> str:
    """Bind the standard copied package and saved launch inputs, not dataset bytes."""
    settings = DavisExperiment.model_validate_json(experiment.read_text())
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
    for raw in frame_files(settings):
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
    settings = DavisExperiment.model_validate_json(experiment.read_text())
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

Original sequence roles: {data["original_sequences"]}; required Train/Validation frame files: {data["required_frame_files"]}. **This review checks frame presence and frozen manifests, not archive SHA-256 or decoded probes.** Launch checks the archive SHA-256 and ten frozen decoded windows; that is not a full cryptographic check of extracted data.

Inspect the composition above, its `data/manifests/`, `llm_config`, `workflow` and this script before launch. The original 60/15/15 sequence split stays unchanged. Fractions select whole clips inside Train or Validation. Epoch train_portion remains 1. **Validation supplies search feedback; Final clips remain unused.**

Data Analysis, literature review and human advice are disabled. The original task Health dispersion gate is blocking; successful training alone does not imply Health PASS. Runtime and scoreability checks also apply.

{launch}

Outputs: `{settings.workspace}`; native launch receipt `.tutorial.json`, notebook log `.console.log` and completion `.notebook-run.json` are siblings of that directory. A direct script launch prints to its terminal. Neither time allowances nor the notebook timeout are a whole-run billing/GPU cap.
"""


def run_demo(experiment: Path, script: Path, *, timeout_seconds: float = 3600) -> dict:
    """Saved script owns execution; shared helper owns cache and process cleanup."""
    from tutorials.supplementary.davis.runner import require_credentials

    settings = DavisExperiment.model_validate_json(experiment.read_text())
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
    settings = DavisExperiment.model_validate_json(experiment.read_text())
    if not disjoint(output, settings.infra_checkout) or not disjoint(
        output, settings.data_dir
    ):
        raise ValueError(
            "plot output must be outside the framework checkout and raw data"
        )
    points = read_progress(settings.workspace)
    scored = [p for p in points if p.score is not None]
    if not scored:
        raise ValueError(
            "No measured Formal score yet. Inspect native records; no zero or substitute score was invented."
        )
    if any(p.metric != "mse" or p.direction != "lower" for p in scored):
        raise ValueError("selected records are not DAVIS mse (lower)")
    return plot_progress(
        settings.workspace,
        output,
        title="DAVIS",
        expected_iterations=settings.iterations,
    )
