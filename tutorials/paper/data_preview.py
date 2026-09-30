"""Plot one training example from a saved tutorial experiment, without execution."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal

import h5py
import matplotlib.pyplot as plt
import numpy as np
import yaml

from tutorials.paper.runner import TutorialExperiment

Task = Literal["tess", "tidmad", "project8", "ligo"]


def plot_training_example(experiment: Path, *, task: Task, row: int = 0):
    """Return a figure and description; read bounded training data, never a test set.

    ``row`` selects a TESS identity, a prepared event, or a 40,000-sample
    TIDMAD window in the first assigned training file (file-holdout only).
    No files are written.
    """
    try:
        return _preview(experiment, task=task, row=row)
    except FileNotFoundError as exc:
        raise ValueError(
            f"Data preview cannot find {exc.filename}. Complete the setup guide's "
            f"data preparation step, or correct data_dir/composition in {experiment}. "
            "Reuse existing local data when available. No download or training was started."
        ) from exc
    except KeyError as exc:
        raise ValueError(
            f"Data preview is missing an expected dataset field or sample: {exc}. "
            f"Check that {experiment} selects a matching task package and prepared data. "
            "Follow the task's data setup guide; no download or training was started."
        ) from exc


def _preview(experiment: Path, *, task: Task, row: int):
    if row < 0:
        raise ValueError("row must be nonnegative")
    if task == "tess":
        settings = TutorialExperiment.model_validate_json(experiment.read_text())
        return _tess(settings, row)
    if task == "tidmad":
        from tutorials.paper.tidmad.runner import TidmadExperiment

        settings = TidmadExperiment.model_validate_json(experiment.read_text())
        return _tidmad(settings, row)
    if task in ("project8", "ligo"):
        from tutorials.paper.prepared.runner import PreparedExperiment

        settings = PreparedExperiment.model_validate_json(experiment.read_text())
        if settings.task != task:
            raise ValueError("task does not match the saved experiment")
        return _prepared(settings, row)
    raise ValueError("choose tess, tidmad, project8 or ligo")


def _check_row(row: int, count: int):
    if not 0 <= row < count:
        raise ValueError(
            f"PREVIEW_ROW={row} is outside the training data. "
            f"Choose PREVIEW_ROW from 0 through {count - 1}; {count} rows are available."
        )


def _panels():
    fig, axes = plt.subplots(2, 1, figsize=(8, 4.8), layout="constrained")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=9)
    return fig, axes


def _tess(settings, row):
    from tasks.phyts_tess.runtime.tess_data_path import normalize_curve

    manifest = (
        settings.composition.parent.parent / "data/manifests/rotation_identity.csv"
    )
    with manifest.open() as stream:
        rows = [item for item in csv.DictReader(stream) if item["split"] == "train"]
    _check_row(row, len(rows))
    selected = rows[row]
    key = f"{selected['gaia_id']}:{selected['sector']}"
    path = settings.data_dir / "tess_rotation_train.npz"
    with np.load(path, allow_pickle=False) as archive:
        raw = archive[key]
    model = normalize_curve(raw, 1024)
    fig, axes = _panels()
    axes[0].plot(raw, color="#2468a0", lw=0.7)
    axes[0].set(
        title=f"TESS training light curve · sector {selected['sector']}",
        ylabel="Released flux",
        xlabel="Observed sample index",
    )
    axes[1].plot(model, color="#2468a0", lw=0.7)
    axes[1].set(
        title="Model input: truncate, normalize, then pad if needed (1,024 samples)",
        ylabel="Normalized flux",
        xlabel="Model sample index",
    )
    description = (
        f"Training identity {key}; {len(raw)} observed samples → input [1, 1024]. "
        f"Target: near-core rotation frequency {float(selected['frot']):.6g} cycles/day. "
        "Flux is stored in tess_rotation_train.npz, keyed by Gaia ID:sector; "
        "rotation_identity.csv supplies the target. "
        "The horizontal axis is sample index, not elapsed days."
    )
    return fig, description


def _tidmad(settings, row):
    from tasks.tidmad.runtime.file_split import FileSplit
    from tasks.tidmad.runtime.profile import TidmadTopology

    if settings.protocol != "file-holdout":
        raise ValueError(
            "The TIDMAD preview requires the file-holdout experiment saved by Quick A. "
            "Pass demo.experiment, not the initial paper-pool experiment."
        )
    composition = yaml.safe_load(settings.composition.read_text())
    split = FileSplit.model_validate(composition["task_data_path"]["config"]["split"])
    profile_path = (
        settings.composition.parent / composition["dataset_profile"]["config"]
    )
    topology = TidmadTopology.model_validate_json(profile_path.read_text())
    path = settings.data_dir / topology.dataset.training_file_name(
        min(split.train_files)
    )
    length = 40000
    _check_row(
        row,
        topology.dataset.segments_per_file
        * topology.dataset.psd_segment_length
        // length,
    )
    start, end = row * length, (row + 1) * length
    channels = [topology.channels.input_channel, topology.channels.target_channel]
    with h5py.File(path) as handle:
        values = [
            np.asarray(
                handle[f"timeseries/{name}/timeseries"][start:end], dtype=np.int16
            )
            + topology.encoding.value_offset
            for name in channels
        ]
    if any(len(value) != length for value in values):
        raise ValueError("the selected training window is incomplete")
    fig, axes = _panels()
    # Display a short contiguous prefix, not a decimation that could alias the signal.
    shown = 600
    time_us = np.arange(shown) / topology.dataset.sampling_frequency * 1e6
    for ax, value, label, color in zip(
        axes,
        values,
        ["Noisy input", "Injected target (not a model prediction)"],
        ["#2468a0", "#bd6a22"],
        strict=True,
    ):
        ax.plot(time_us, value[:shown], lw=0.8, color=color)
        ax.set(
            title=label,
            xlabel="Time within window (µs)",
            ylabel=f"ADC value + {topology.encoding.value_offset}",
        )
    description = (
        f"{path.name}, training window {row}: paired input/target [40000] arrays. "
        f"Stored {topology.encoding.storage_dtype} ADC values are shifted by "
        f"+{topology.encoding.value_offset} for the model. "
        f"HDF5 paths: timeseries/{channels[0]}/timeseries (input) and "
        f"timeseries/{channels[1]}/timeseries (target). "
        "Only the first 600 samples are drawn; no holdout or final-test data is read."
    )
    return fig, description


def _prepared(settings, row):
    inputs = np.load(
        settings.data_dir / "training/inputs.npy", mmap_mode="r", allow_pickle=False
    )
    targets = np.load(
        settings.data_dir / "training/targets.npy", mmap_mode="r", allow_pickle=False
    )
    _check_row(row, min(len(inputs), len(targets)))
    x, target = inputs[row], float(targets[row, 0])
    expected = (4, 24576) if settings.task == "project8" else (2, 1024)
    if x.shape != expected:
        raise ValueError(f"expected {settings.task} input {expected}; got {x.shape}")
    fig, axes = _panels()
    if settings.task == "project8":
        for i, label in enumerate(["I", "Q"]):
            axes[0].plot(x[i, :1024], lw=0.7, label=label, alpha=0.8)
        axes[0].set(
            title="Time view: first 1,024 of 24,576 samples",
            xlabel="Time sample index",
            ylabel="Normalized amplitude",
        )
        for i, label in [(2, "FFT real"), (3, "FFT imaginary")]:
            axes[1].plot(x[i], lw=0.6, label=label, alpha=0.8)
        axes[1].set(
            title="Frequency view: full complex FFT in stored order",
            xlabel="FFT bin (unshifted)",
            ylabel="Orthonormal FFT amplitude",
        )
        for ax in axes:
            ax.legend(frameon=False, fontsize=9, loc="upper right")
        description = (
            f"Training event {row}: input [4, 24576], target [1] = {target:.6g} eV. "
            "Channels 0/1 are time I/Q; channels 2/3 are FFT real/imaginary values. "
            "Both views describe the same event; time samples and FFT bins are different axes."
        )
    else:
        for i, ax in enumerate(axes):
            ax.plot(x[i], lw=0.8, color=["#2468a0", "#bd6a22"][i])
            ax.set(
                title=f"Whitened detector channel {i}",
                xlabel="Sample index within 1,024-sample crop",
                ylabel="Prepared amplitude",
            )
        description = (
            f"Training event {row}: input [2, 1024], target [1] = {target:.6g} solar masses "
            "(chirp mass). Both detector channels belong to the same event. "
            "These are the prepared whitened/cropped inputs, not raw detector strain."
        )
    description += (
        " Files: training/inputs.npy [N, C, L] and training/targets.npy [N, 1]."
    )
    return fig, description
