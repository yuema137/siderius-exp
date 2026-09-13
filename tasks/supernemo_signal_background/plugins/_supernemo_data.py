"""Pure SuperNEMO scope materialization and event-dataset logic."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py
import numpy as np
import torch
from pydantic import BaseModel, ConfigDict, Field
from torch.utils.data import Dataset

from .energy_matched_auc import (
    energy_balanced_indices,
    energy_matched_roc,  # noqa: F401 -- public arithmetic export for metric consumers
    weighted_roc,  # noqa: F401 -- public arithmetic export for metric consumers
)

PROCESSES = ("0nubb", "2nubb", "Bi214", "Tl208")
FILES = {
    "0nubb": "data_0nubb_merged.h5",
    "2nubb": "data_2nubb_merged.h5",
    "Bi214": "data_Bi214_merged.h5",
    "Tl208": "data_Tl208_merged.h5",
}
LABELS = {"0nubb": 1, "2nubb": 0, "Bi214": 0, "Tl208": 0}
SPLITS = {"train": 0, "validation": 1}
MAX_HITS = 224
ENERGY_EDGES = np.arange(0.0, 3625.0, 25.0)


class SuperNemoScope(BaseModel):
    """Compact deterministic scope; identities are resolved from external indexes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: str
    portion: float = Field(gt=0, le=1)
    seed: int | None = None
    max_samples: int | None = Field(default=None, ge=2)


class MaterializedEvents(BaseModel):
    """Selected event identities and task-owned scientific values."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    process_ids: np.ndarray
    event_indices: np.ndarray
    event_ids: np.ndarray
    row_starts: np.ndarray
    hit_counts: np.ndarray
    event_features: np.ndarray
    energy_sum: np.ndarray
    labels: np.ndarray


def _choose(values: np.ndarray, portion: float, seed: int | None) -> np.ndarray:
    keep = max(1, round(values.size * portion))
    if keep >= values.size:
        return values
    if seed is None:
        return values[:keep]
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(values, size=keep, replace=False))


def _balanced_cap(
    indices: np.ndarray,
    labels: np.ndarray,
    energy_sum: np.ndarray,
    max_samples: int | None,
) -> np.ndarray:
    """Cap a balanced selection while retaining class parity in every bin."""
    if max_samples is None or indices.size <= max_samples:
        return indices
    pair_budget = max_samples // 2
    bin_ids = np.searchsorted(ENERGY_EDGES, energy_sum, side="right") - 1
    pairs_by_bin: list[tuple[np.ndarray, np.ndarray]] = []
    for bin_id in np.unique(bin_ids[indices]):
        in_bin = indices[bin_ids[indices] == bin_id]
        signal = in_bin[labels[in_bin] == 1]
        background = in_bin[labels[in_bin] == 0]
        available = min(signal.size, background.size)
        if available:
            pairs_by_bin.append((signal[:available], background[:available]))
    selected: list[int] = []
    depth = 0
    while pair_budget:
        added = False
        for signal, background in pairs_by_bin:
            if depth >= signal.size:
                continue
            selected.extend((int(signal[depth]), int(background[depth])))
            pair_budget -= 1
            added = True
            if pair_budget == 0:
                break
        if not added:
            break
        depth += 1
    return np.sort(np.asarray(selected, dtype=np.int64))


def materialize_scope(
    scope: SuperNemoScope, data_dir: str | Path, train_portion: float = 1.0
) -> MaterializedEvents:
    """Resolve, portion, and exactly energy-balance one declared scope."""
    root = Path(data_dir)
    parts: dict[str, list[np.ndarray]] = {
        key: []
        for key in (
            "process_ids",
            "event_indices",
            "event_ids",
            "row_starts",
            "hit_counts",
            "event_features",
            "energy_sum",
            "labels",
        )
    }
    for process_id, process in enumerate(PROCESSES):
        with np.load(root / "event_indexes" / f"{process}_event_index.npz") as index:
            available = np.flatnonzero(index["splits"] == SPLITS[scope.role])
            selected = _choose(available, scope.portion, scope.seed)
            selected = _choose(selected, train_portion, scope.seed)
            parts["process_ids"].append(
                np.full(selected.size, process_id, dtype=np.uint8)
            )
            parts["event_indices"].append(selected.astype(np.int64))
            parts["event_ids"].append(index["event_ids"][selected])
            parts["row_starts"].append(index["row_starts"][selected])
            parts["hit_counts"].append(index["hit_counts"][selected])
            parts["event_features"].append(index["event_features"][selected])
            parts["energy_sum"].append(index["energy_sum"][selected])
            parts["labels"].append(
                np.full(selected.size, LABELS[process], dtype=np.uint8)
            )
    merged = {key: np.concatenate(value) for key, value in parts.items()}
    balanced = energy_balanced_indices(
        merged["labels"], merged["energy_sum"], ENERGY_EDGES
    )
    selected = _balanced_cap(
        balanced.indices,
        merged["labels"],
        merged["energy_sum"],
        scope.max_samples,
    )
    return MaterializedEvents(**{key: value[selected] for key, value in merged.items()})


class SuperNemoEventDataset(Dataset):
    """One fixed-shape detector tensor and binary class target per event."""

    def __init__(self, events: MaterializedEvents, data_dir: str | Path) -> None:
        self.events = events
        self.data_dir = Path(data_dir)
        self._handles: dict[int, h5py.File] = {}

    def __len__(self) -> int:
        return int(self.events.labels.size)

    def _handle(self, process_id: int) -> h5py.File:
        if process_id not in self._handles:
            self._handles[process_id] = h5py.File(
                self.data_dir / FILES[PROCESSES[process_id]], "r"
            )
        return self._handles[process_id]

    def __getitem__(self, item: int) -> tuple[torch.Tensor, int]:
        process_id = int(self.events.process_ids[item])
        start = int(self.events.row_starts[item])
        count = min(int(self.events.hit_counts[item]), MAX_HITS)
        handle = self._handle(process_id)
        result = np.zeros((MAX_HITS, 11), dtype=np.float32)
        result[:count, 0] = 1.0
        scales = (405.0, 2464.0, 1480.0, 23.543)
        for column, (key, scale) in enumerate(
            zip(("tX", "tY", "tZ", "tR"), scales, strict=True), start=1
        ):
            values = np.asarray(handle[key][start : start + count], np.float32)
            if key == "tR":
                result[:count, 5] = ~np.isfinite(values)
                values = np.nan_to_num(values, nan=0.0)
            result[:count, column] = values / scale
        event = self.events.event_features[item] / np.array(
            [3500.0, 3500.0, 5000.0, 3000.0, 180.0], dtype=np.float32
        )
        result[:count, 6:11] = event
        return torch.from_numpy(result), int(self.events.labels[item])

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_handles"] = {}
        return state
