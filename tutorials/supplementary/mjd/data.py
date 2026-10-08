"""Read-only official-file checks and previews through the selected MJD task."""

from __future__ import annotations

import subprocess
import sys
from typing import Literal

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field

from tutorials.shared.runtime import ROOT
from tutorials.supplementary.mjd.settings import MjdExperiment

OFFICIAL_MANIFEST = ROOT / "tasks/majorana_low_avse/declared/dataset_manifest.json"


class FileEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bytes: int = Field(gt=0)
    md5: str = Field(pattern=r"^[0-9a-f]{32}$")
    role: Literal["train", "test", "unlabeled"]


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record: int
    doi: str
    files: dict[str, FileEntry]


class ScopeCount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    official_role: Literal["train", "test"]
    fraction: float
    seed: int
    samples: int
    rejected: int
    accepted: int


def verify_files(settings: MjdExperiment, *, hashes: bool = False) -> dict:
    """All supervised files remain required; launch invokes the task MD5 owner."""
    selected = settings.composition.parent.parent / "declared/dataset_manifest.json"
    official = DatasetManifest.model_validate_json(OFFICIAL_MANIFEST.read_text())
    manifest = DatasetManifest.model_validate_json(selected.read_text())
    if manifest != official:
        raise ValueError(
            "copied dataset_manifest.json differs from the official task authority; restore it"
        )
    supervised = {
        name: entry
        for name, entry in manifest.files.items()
        if entry.role != "unlabeled"
    }
    for name, entry in supervised.items():
        path = settings.data_dir / name
        if not path.is_file():
            raise ValueError(
                f"Missing official input: {path}. Stage all 16 Train and 6 Test files first."
            )
        if path.stat().st_size != entry.bytes:
            raise ValueError(
                f"Official byte size differs: {path}; verify the original download"
            )
    if hashes:
        # Do not duplicate scientific integrity arithmetic or trust an edited verifier copy.
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tasks/majorana_low_avse/tools/verify_dataset.py"),
                str(settings.data_dir),
                str(OFFICIAL_MANIFEST),
                "--supervised-only",
            ],
            check=True,
        )
    return {
        "supervised_files": len(supervised),
        "bytes": sum(e.bytes for e in supervised.values()),
        "verification": "size_and_md5" if hashes else "size_only",
        "manifest": str(selected),
    }


def selected_task(settings: MjdExperiment):
    from workflows.task_composition import compose_task_data_path_from_manifest

    declaration = yaml.safe_load(settings.composition.read_text())
    if declaration.get("task_health") != {"none": True}:
        raise ValueError("this tutorial requires MJD's explicit no-Health declaration")
    path = compose_task_data_path_from_manifest(str(settings.composition))
    if path.task_data_path_id != "majorana_low_avse":
        raise ValueError("select the Majorana Low-AvsE composition")
    return path


def scope_counts(settings: MjdExperiment, *, seed: int = 42) -> list[ScopeCount]:
    """Ask the actual copied task for illustrative populations, never resplit data."""
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
        ("Trial evaluation", "test", settings.trial_eval_fraction, "trial"),
        ("Formal training", "train", settings.formal_train_fraction, "formal"),
        ("Formal evaluation", "test", settings.formal_eval_fraction, "formal"),
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
                EpochSamplingParams(data_dir=str(settings.data_dir), train_portion=1.0),
            )
        else:
            scope = path.build_eval_scope(request)
            dataset = path.validation_dataset(
                scope, EvalMaterializationParams(data_dir=str(settings.data_dir))
            )
        labels = dataset.events.labels
        counts = np.bincount(labels, minlength=2)
        reports.append(
            ScopeCount(
                name=name,
                official_role=role,
                fraction=fraction,
                seed=seed,
                samples=len(dataset),
                rejected=int(counts[0]),
                accepted=int(counts[1]),
            )
        )
    return reports


def show_waveform(settings: MjdExperiment, *, row: int = 0):
    """One selected Train waveform, before and after the task's own normalization."""
    import h5py
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
        scope, EpochSamplingParams(data_dir=str(settings.data_dir), train_portion=1.0)
    )
    if not 0 <= row < len(dataset):
        raise ValueError(f"PREVIEW_ROW must be from 0 through {len(dataset) - 1}")
    tensor, label = dataset[row]  # Native task owns the waveform transform.
    events = dataset.events
    filename = f"MJD_Train_{int(events.file_indices[row])}.hdf5"
    source_row = int(events.row_indices[row])
    with h5py.File(settings.data_dir / filename, "r") as handle:
        raw = np.asarray(handle["raw_waveform"][source_row], dtype=np.float32)
    figure, axes = plt.subplots(2, 1, figsize=(9, 4.5), sharex=True)
    axes[0].plot(raw, lw=0.8)
    axes[0].set_ylabel("Raw ADC")
    axes[0].axvspan(0, 499, alpha=0.12, color="orange", label="500-sample baseline")
    axes[0].legend(loc="upper left")
    axes[1].plot(tensor[0].numpy(), lw=0.8)
    axes[1].set_ylabel("Model input")
    axes[1].set_xlabel("Sample index (no timing field supplied)")
    figure.suptitle(f"Train only: {filename}, row {source_row}; Low-AvsE label {label}")
    figure.tight_layout()
    return figure
