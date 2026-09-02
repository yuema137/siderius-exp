"""Pure scope materialization and waveform loading for Majorana Low-AvsE."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch
from pydantic import BaseModel, ConfigDict, Field
from torch.utils.data import Dataset

ENERGY_EDGES = np.arange(0.0, 5025.0, 25.0)
FILES = {
    "train": tuple(f"MJD_Train_{index}.hdf5" for index in range(16)),
    "test": tuple(f"MJD_Test_{index}.hdf5" for index in range(6)),
}


class MajoranaScope(BaseModel):
    """Compact deterministic scope resolved from official file partitions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    portion: float = Field(gt=0, le=1)
    seed: int | None = None
    max_samples: int | None = Field(default=None, ge=2)


class MaterializedEvents(BaseModel):
    """Selected identities plus task-owned labels and matching energies."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    role: str
    file_indices: np.ndarray
    row_indices: np.ndarray
    event_ids: np.ndarray
    labels: np.ndarray
    energies: np.ndarray


def _choose(values: np.ndarray, portion: float, seed: int | None) -> np.ndarray:
    keep = max(1, round(values.size * portion))
    if keep >= values.size:
        return values
    # A prefix would overrepresent early official files. Seed zero gives an
    # explicit, reproducible whole-partition snapshot when no caller seed exists.
    rng = np.random.default_rng(0 if seed is None else seed)
    return np.sort(rng.choice(values, size=keep, replace=False))


def _balanced_indices(
    labels: np.ndarray, energies: np.ndarray, max_samples: int | None
) -> np.ndarray:
    """Select equal deterministic class counts in each fixed energy bin."""
    bins = np.searchsorted(ENERGY_EDGES, energies, side="right") - 1
    parts: list[np.ndarray] = []
    for bin_id in np.unique(bins):
        if bin_id < 0 or bin_id >= ENERGY_EDGES.size - 1:
            continue
        members = np.flatnonzero(bins == bin_id)
        negative = members[labels[members] == 0]
        positive = members[labels[members] == 1]
        count = min(negative.size, positive.size)
        if count:
            parts.extend((negative[:count], positive[:count]))
    if not parts:
        raise ValueError("no 25-keV energy bin contains both Low-AvsE classes")
    selected = np.sort(np.concatenate(parts))
    if max_samples is None or selected.size <= max_samples:
        return selected
    # Round-robin pairs retain exact class equality in every retained bin.
    pair_limit = max_samples // 2
    kept: list[int] = []
    depth = 0
    grouped: list[tuple[np.ndarray, np.ndarray]] = []
    selected_bins = bins[selected]
    for bin_id in np.unique(selected_bins):
        members = selected[selected_bins == bin_id]
        grouped.append((members[labels[members] == 0], members[labels[members] == 1]))
    while pair_limit:
        added = False
        for negative, positive in grouped:
            if depth >= negative.size:
                continue
            kept.extend((int(negative[depth]), int(positive[depth])))
            pair_limit -= 1
            added = True
            if not pair_limit:
                break
        if not added:
            break
        depth += 1
    return np.sort(np.asarray(kept, dtype=np.int64))


def materialize_scope(
    scope: MajoranaScope, data_dir: str | Path, train_portion: float = 1.0
) -> MaterializedEvents:
    """Resolve official Train or Test files and apply exact energy balance."""
    root = Path(data_dir)
    if scope.role not in FILES:
        raise ValueError(f"unsupported Majorana scope role: {scope.role}")
    file_indices: list[np.ndarray] = []
    row_indices: list[np.ndarray] = []
    event_ids: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    energies: list[np.ndarray] = []
    for file_index, name in enumerate(FILES[scope.role]):
        with h5py.File(root / name, "r") as handle:
            count = int(handle["raw_waveform"].shape[0])
            file_indices.append(np.full(count, file_index, dtype=np.uint8))
            row_indices.append(np.arange(count, dtype=np.int32))
            event_ids.append(np.asarray(handle["id"][:], dtype=np.int64))
            labels.append(np.asarray(handle["psd_label_low_avse"][:], dtype=np.uint8))
            energies.append(np.asarray(handle["energy_label"][:], dtype=np.float32))
    merged = {
        "file_indices": np.concatenate(file_indices),
        "row_indices": np.concatenate(row_indices),
        "event_ids": np.concatenate(event_ids),
        "labels": np.concatenate(labels),
        "energies": np.concatenate(energies),
    }
    available = np.arange(merged["labels"].size, dtype=np.int64)
    selected = _choose(available, scope.portion, scope.seed)
    selected = _choose(selected, train_portion, scope.seed)
    balanced = _balanced_indices(
        merged["labels"][selected], merged["energies"][selected], scope.max_samples
    )
    chosen = selected[balanced]
    return MaterializedEvents(
        role=scope.role, **{key: value[chosen] for key, value in merged.items()}
    )


class MajoranaWaveformDataset(Dataset):
    """One baseline-normalized raw waveform and Low-AvsE label per event."""

    def __init__(self, events: MaterializedEvents, data_dir: str | Path) -> None:
        self.events = events
        self.data_dir = Path(data_dir)
        self._handles: dict[int, h5py.File] = {}

    def __len__(self) -> int:
        return int(self.events.labels.size)

    def _handle(self, file_index: int) -> h5py.File:
        if file_index not in self._handles:
            self._handles[file_index] = h5py.File(
                self.data_dir / FILES[self.events.role][file_index], "r"
            )
        return self._handles[file_index]

    def __getitem__(self, item: int) -> tuple[torch.Tensor, int]:
        file_index = int(self.events.file_indices[item])
        row_index = int(self.events.row_indices[item])
        waveform = np.asarray(
            self._handle(file_index)["raw_waveform"][row_index], dtype=np.float32
        )
        baseline = waveform[:500]
        waveform = waveform - float(np.mean(baseline))
        scale = max(float(np.std(baseline)), 1.0)
        waveform = waveform / scale
        return torch.from_numpy(waveform[None, :]), int(self.events.labels[item])

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_handles"] = {}
        return state
