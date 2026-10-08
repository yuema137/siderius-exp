"""Notebook delegation and local visualization; all execution stays in scripts."""

from __future__ import annotations

import hashlib
import shlex
from pathlib import Path

from tutorials.shared.progress import plot_progress, read_progress
from tutorials.shared.saved_run import run_saved_script
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

    def ready() -> None:
        from tutorials.supplementary.pet.runner import require_credentials

        require_credentials(settings.llm_config)

    return run_saved_script(
        script=script,
        workspace=settings.workspace,
        digest=input_digest(experiment, script),
        ready=ready,
        timeout_seconds=timeout_seconds,
    )


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
