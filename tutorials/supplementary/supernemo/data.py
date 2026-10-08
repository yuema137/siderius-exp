"""Inspect prepared SuperNEMO data through the selected task's event loader."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict

from tutorials.supplementary.supernemo.prepare import (
    SOURCE_MANIFEST,
    SourceManifest,
    verify_prepared,
)
from tutorials.supplementary.supernemo.settings import SuperNemoExperiment


class ScopeCount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    role: str
    fraction: float
    seed: int
    samples: int
    background: int
    signal: int


def verify_files(settings: SuperNemoExperiment, *, hashes: bool = False) -> dict:
    selected = settings.composition.parent.parent / "declared/source_files.json"
    if SourceManifest.model_validate_json(
        selected.read_text()
    ) != SourceManifest.model_validate_json(SOURCE_MANIFEST.read_text()):
        raise ValueError(
            "Copied source_files.json differs from official authority; restore it"
        )
    receipt = verify_prepared(settings.data_dir, hashes=hashes)
    return {
        "source_files": len(receipt.raw_files),
        "bytes": sum(f.bytes for f in receipt.raw_files.values()),
        "verification": "raw_md5_and_index_hashes"
        if hashes
        else "raw_bindings_and_index_hashes",
        "prepared_data": str(settings.data_dir),
    }


def selected_task(settings: SuperNemoExperiment):
    from workflows.task_composition import compose_task_data_path_from_manifest

    declaration = yaml.safe_load(settings.composition.read_text())
    if declaration.get("task_health") != {"none": True}:
        raise ValueError(
            "This tutorial requires SuperNEMO's explicit no-Health declaration"
        )
    path = compose_task_data_path_from_manifest(str(settings.composition))
    if path.task_data_path_id != "supernemo_signal_background":
        raise ValueError("Select the SuperNEMO signal-background composition")
    return path


def scope_counts(settings: SuperNemoExperiment, *, seed: int = 42) -> list[ScopeCount]:
    from execute_tools.task_data_path import (
        EpochSamplingParams,
        EvalMaterializationParams,
        ScopeBuildRequest,
    )

    verify_files(settings)
    path = selected_task(settings)
    reports = []
    for name, role, fraction, round_kind in (
        ("Trial training", "train", settings.trial_train_fraction, "trial"),
        ("Trial evaluation", "validation", settings.trial_eval_fraction, "trial"),
        ("Formal training", "train", settings.formal_train_fraction, "formal"),
        ("Formal evaluation", "validation", settings.formal_eval_fraction, "formal"),
    ):
        request = ScopeBuildRequest(
            round_kind=round_kind,
            selection_strategy="snapshot",
            portion=fraction,
            seed=seed,
        )
        if role == "train":
            scope = path.build_training_scope(request)
            dataset = path.training_dataset(
                scope,
                EpochSamplingParams(
                    data_dir=str(settings.data_dir),
                    train_portion=settings.train_portion,
                ),
            )
        else:
            scope = path.build_eval_scope(request)
            dataset = path.validation_dataset(
                scope, EvalMaterializationParams(data_dir=str(settings.data_dir))
            )
        counts = np.bincount(dataset.events.labels, minlength=2)
        reports.append(
            ScopeCount(
                name=name,
                role=role,
                fraction=fraction,
                seed=seed,
                samples=len(dataset),
                background=int(counts[0]),
                signal=int(counts[1]),
            )
        )
    return reports


def show_event(settings: SuperNemoExperiment, *, row: int = 0):
    """Plot one Train event's actual capped/padded model input; no final-test access."""
    import matplotlib.pyplot as plt
    from execute_tools.task_data_path import EpochSamplingParams, ScopeBuildRequest

    verify_files(settings)
    path = selected_task(settings)
    scope = path.build_training_scope(
        ScopeBuildRequest(
            round_kind="trial",
            selection_strategy="snapshot",
            portion=settings.trial_train_fraction,
            seed=42,
        )
    )
    dataset = path.training_dataset(
        scope,
        EpochSamplingParams(
            data_dir=str(settings.data_dir), train_portion=settings.train_portion
        ),
    )
    if not 0 <= row < len(dataset):
        raise ValueError(f"PREVIEW_ROW must be between 0 and {len(dataset) - 1}")
    tensor, label = dataset[row]
    values = tensor.numpy()
    valid = values[:, 0].astype(bool)
    hits = int(dataset.events.hit_counts[row])
    event_id = int(dataset.events.event_ids[row])
    process_id = int(dataset.events.process_ids[row])
    source_file = Path(dataset._handle(process_id).filename).name
    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].scatter(values[valid, 1], values[valid, 2], s=12)
    axes[0].set(
        xlabel="Task-scaled tX",
        ylabel="Task-scaled tY",
        title=f"{source_file}, event {event_id}\nTrain: {int(valid.sum())}/{hits} retained hits",
    )
    image = axes[1].imshow(
        values, aspect="auto", interpolation="nearest", cmap="coolwarm"
    )
    axes[1].set(
        xlabel="Declared model feature (11 columns)",
        ylabel="Padded hit index",
        title=f"Model input [224,11]; class {label}",
    )
    figure.colorbar(image, ax=axes[1], label="Task-scaled value")
    figure.tight_layout()
    return figure
