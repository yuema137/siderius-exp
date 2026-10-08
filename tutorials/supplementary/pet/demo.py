"""Notebook delegation and local visualization; all execution stays in scripts."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import signal
import subprocess
import time
from pathlib import Path

import psutil

from tutorials.shared.progress import plot_progress, read_progress
from tutorials.supplementary.pet.data import inspect_data, read_splits
from tutorials.supplementary.pet.project import validate_launcher
from tutorials.supplementary.pet.settings import PetExperiment


def input_digest(experiment: Path, script: Path) -> str:
    """Bind reuse to all editable task/routing/workflow/script inputs, not JSON alone."""
    settings = PetExperiment.model_validate_json(experiment.read_text())
    task = settings.composition.parent.parent
    files = [experiment, script, settings.llm_config, settings.workflow]
    files += sorted(
        p
        for p in task.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def review(experiment: Path, script: Path) -> str:
    """Show every saved setting and each exact command before execution."""
    settings = PetExperiment.model_validate_json(experiment.read_text())
    validate_launcher(experiment, script)
    reports = inspect_data(settings.composition, settings.data_dir)
    values = "\n".join(
        f"| `{key}` | `{value}` |"
        for key, value in settings.model_dump(mode="json").items()
    )
    counts = ", ".join(
        f"{role}: {r.count} images ({len(r.per_class)} breeds)"
        for role, r in reports.items()
    )
    return f"""Saved input: `{experiment}`

| Setting | Effective value |
|---|---|
{values}

{counts}. Final is separate and is **not** scored during search.

Data Analysis, literature review and human advice are **disabled**. This fixed workflow does not use a workflow sandbox. Generated models run through native execution checks.

Inspect the task composition and its referenced CSVs, then `llm/agents.json` (model/provider/strategy, never API keys), `experiments/workflow.json` (fixed workflow), and the experiment above (run choices). The native preview below prints all additional workflow flags.

Preview (no API/GPU):
```bash
bash {shlex.quote(str(script))}
```

Launch the saved experiment (API/GPU effects):
```bash
bash {shlex.quote(str(script))} --launch
```

Outputs: `{settings.workspace}`. When this notebook launches the script, its console log and completion receipt sit beside this directory. A direct terminal launch prints to your terminal and saves a `.tutorial.json` launch receipt. Plot exports go to your project's `plots/` directory.
"""


def run_demo(experiment: Path, script: Path, *, timeout_seconds: float = 3600) -> dict:
    """Invoke the same saved shell entrypoint; interruption kills its process group.

    This timeout is a notebook convenience, not API billing or GPU accounting.
    Real validation uses a separately qualified operator budget guard.
    """
    settings = PetExperiment.model_validate_json(experiment.read_text())
    validate_launcher(experiment, script)
    workspace = settings.workspace
    completion = workspace.with_suffix(".notebook-run.json")
    log_path = workspace.with_suffix(".console.log")
    digest = input_digest(experiment, script)
    if completion.exists():
        result = json.loads(completion.read_text())
        if result["input_sha256"] != digest:
            raise ValueError(
                "Inputs changed after this run. Keep old results and select a fresh workspace/run name before executing."
            )
        if not workspace.is_dir():
            raise ValueError(
                "Completed workspace is missing; restore it or choose a new run"
            )
        if result["exit_code"] != 0:
            raise RuntimeError(
                f"Previous script run failed; inspect {log_path} before selecting a new workspace"
            )
        print(f"Reusing recorded result without API/GPU work: {workspace}")
        return result
    if workspace.exists() or log_path.exists():
        raise ValueError(
            f"Existing or interrupted run; inspect {log_path}. Nothing was relaunched."
        )
    from tutorials.supplementary.pet.runner import require_credentials

    require_credentials(settings.llm_config)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with log_path.open("x") as log:
        process = subprocess.Popen(
            ["bash", str(script), "--launch"],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        print(f"Running saved script: {script}\nLive log: {log_path}", flush=True)
        try:
            while True:
                remaining = timeout_seconds - (time.monotonic() - start)
                if remaining <= 0:
                    raise TimeoutError(
                        "Notebook time limit reached; stopped the entire run process group"
                    )
                try:
                    code = process.wait(timeout=min(30, remaining))
                    break
                except subprocess.TimeoutExpired:
                    print(
                        f"Running: {(time.monotonic() - start) / 60:.1f} min; inspect {log_path.name}",
                        flush=True,
                    )
        except BaseException:
            # Measurement workers may start their own session; killpg alone
            # cannot reach them. Capture descendants before terminating parents.
            try:
                descendants = psutil.Process(process.pid).children(recursive=True)
            except psutil.NoSuchProcess:
                descendants = []
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            for child in descendants:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            _, alive = psutil.wait_procs(descendants, timeout=5)
            for child in alive:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
    result = {
        "input_sha256": digest,
        "exit_code": code,
        "elapsed_seconds": time.monotonic() - start,
        "workspace": str(workspace),
        "log": str(log_path),
    }
    with completion.open("x") as stream:
        json.dump(result, stream, indent=2)
    if code:
        raise RuntimeError(
            f"Saved script exited {code}. Inspect {log_path}; do not silently rerun an incomplete workspace."
        )
    return result


def plot_results(experiment: Path, output: Path):
    settings = PetExperiment.model_validate_json(experiment.read_text())
    points = read_progress(settings.workspace)
    if not any(p.score is not None for p in points):
        raise ValueError(
            "No measured Formal score yet. Inspect the run log/records; no score was invented."
        )
    return plot_progress(
        settings.workspace,
        output,
        title="Oxford-IIIT Pet",
        expected_iterations=settings.iterations,
    )


def show_images(experiment: Path):
    """Render local training images after the task's actual CPU transformation."""
    import matplotlib.pyplot as plt
    from execute_tools.task_data_path import EpochSamplingParams, ScopeBuildRequest
    from workflows.task_composition import compose_task_data_path_from_manifest

    settings = PetExperiment.model_validate_json(experiment.read_text())
    rows = read_splits(settings.composition)["train"]
    chosen = [
        next(row for row in rows if row.class_index == index)
        for index in (0, 5, 10, 15, 20, 25)
    ]
    data_path = compose_task_data_path_from_manifest(str(settings.composition))
    scope = data_path.build_training_scope(
        ScopeBuildRequest(
            round_kind="trial",
            selection_strategy="target",
            portion=1.0,
            target_partitions=tuple(rows.index(row) for row in chosen),
        )
    )
    dataset = data_path.training_dataset(
        scope,
        EpochSamplingParams(
            data_dir=str(settings.data_dir),
            train_portion=1.0,
        ),
    )
    figure, axes = plt.subplots(2, 3, figsize=(9, 6))
    for index, (row, axis) in enumerate(zip(chosen, axes.flat, strict=True)):
        tensor, label = dataset[index]
        if label != row.class_index:
            raise ValueError("Task preview labels differ from the selected manifest")
        axis.imshow(tensor.permute(1, 2, 0).numpy())
        axis.set_title(
            f"{row.image_id.rsplit('_', 1)[0]}\nclass_index={row.class_index}",
            fontsize=9,
        )
        axis.axis("off")
    figure.suptitle("Local training images → [3, 144, 144] float32 in [0, 1]")
    figure.tight_layout()
    return figure
