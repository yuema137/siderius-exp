"""Explain the exact saved files and parameters before a prepared demo launch."""

from __future__ import annotations

import shlex
from pathlib import Path

import yaml

from tasks.shared.prepared_regression import PreparedDeclaration
from tutorials.paper.launch_review import _binding
from tutorials.paper.prepared.runner import PreparedExperiment, credential_status
from tutorials.paper.runner import ROOT


def launch_review(config: Path, script: Path, *, task: str) -> str:
    config, script = config.resolve(), script.resolve()
    if not config.is_file() or not script.is_file():
        return (
            f"**STOP: save the experiment and launcher first:** `{config}`, `{script}`"
        )
    settings = PreparedExperiment.model_validate_json(config.read_text())
    if settings.task != task:
        raise ValueError("selected task and saved experiment disagree")
    text = script.read_text()
    if (
        Path(_binding(text, "EXPERIMENT")).resolve() != config
        or Path(_binding(text, "EXP_CHECKOUT")).resolve() != ROOT
    ):
        raise ValueError("script selects a different experiment or checkout")
    expected = 'exec "$EXP_CHECKOUT/.venv/bin/python" -B -m tutorials.paper.prepared.runner --experiment "$EXPERIMENT" "$@"'
    if expected not in text.splitlines():
        raise ValueError("script is not the prepared-demo launcher")
    paths = {
        "Experiment JSON": config,
        "Task entry YAML": settings.composition,
        "LLM routing (no keys)": settings.llm_config,
        "Literature-review settings": settings.literature_config,
        "Shell script to execute": script,
        "Data and row membership": settings.data_dir / "manifest.json",
    }
    array_paths = [
        settings.data_dir / name
        for name in (
            "training/inputs.npy",
            "training/targets.npy",
            "evaluator/validation/inputs.npy",
            "evaluator/validation/targets.npy",
            "evaluator/validation/loss_indices.npy",
        )
    ]
    missing = [
        path
        for path in [*paths.values(), *array_paths]
        if path is None or not path.is_file()
    ]
    lines = ["### Saved files to check", "", "| File | Actual path |", "|---|---|"]
    lines += [f"| {label} | `{path}` |" for label, path in paths.items()]
    lines += [
        "",
        "### Parameters reloaded from the saved JSON",
        "",
        "| Parameter | Value |",
        "|---|---|",
    ]
    for name in (
        "run_name",
        "gpu",
        "iterations",
        "epochs",
        "batch_size",
        "trial_minutes",
        "formal_minutes",
        "vram_gib",
        "trial_vram_gib",
        "formal_vram_gib",
        "trial_train_fraction",
        "trial_val_fraction",
        "formal_train_fraction",
        "formal_val_fraction",
    ):
        lines.append(f"| `{name}` | `{getattr(settings, name)}` |")
    lines += [
        "",
        "Both stages select the full training scope per epoch, then apply native batching with the saved batch_size; LIGO may drop a partial tail batch. Fractions sample within the saved split; they do not change membership. Per-stage VRAM overrides use vram_gib when null. Training-validation loss uses a fixed 10% snapshot, independent of Trial/Formal scoring fractions.",
        "Human advice and Data Analysis are disabled; Literature Review is enabled.",
        "",
        f"Required exported key presence: `{credential_status(settings)}`. Values are never displayed.",
    ]
    if not missing:
        declaration = PreparedDeclaration.model_validate_json(
            (settings.composition.parent.parent / "declared/prepared.json").read_text()
        )
        lines += [
            "",
            f"Saved population: **{declaration.train_count} training / {declaration.validation_count} validation**; **{len(declaration.loss_indices)}** fixed epoch-loss validation rows.",
            f"Input shape: `[B, {declaration.channels}, {declaration.length}]`; output: `[B, 1]`.",
        ]
    if missing:
        lines += [
            "",
            "**STOP: prepare data and restore missing files before launch:**",
            *[f"- `{path}`" for path in missing],
        ]
    else:
        lines += [
            "",
            "### Exact terminal commands",
            "",
            "Preview only:",
            "```bash",
            shlex.join(["bash", str(script)]),
            "```",
            "Start this saved experiment (paid API + GPU work):",
            "```bash",
            shlex.join(["bash", str(script), "--launch"]),
            "```",
            "Quick B invokes this same script. Do not also run the terminal command for the same demo.",
        ]
    lines += [
        "",
        f"Results: `{settings.workspace}`",
        f"Console log for Quick B: `{settings.workspace}.console.log`",
        "An existing workspace is never silently restarted. Choose a new DEMO_NAME for another run.",
    ]
    return "\n".join(lines)


def plot_demo(experiment: Path, output: Path):
    """Use the selected task's explicit absence of Health checks, not missing records."""
    from tutorials.paper.progress import plot_progress

    settings = PreparedExperiment.model_validate_json(experiment.read_text())
    composition = yaml.safe_load(settings.composition.read_text())
    if composition.get("task_health") != {"none": True}:
        raise ValueError(
            "this demo plot requires an explicitly declared no-Health task"
        )
    return plot_progress(
        settings.workspace,
        output,
        title="Project8" if settings.task == "project8" else "LIGO",
        expected_iterations=settings.iterations,
        health_policy="none",
    )
