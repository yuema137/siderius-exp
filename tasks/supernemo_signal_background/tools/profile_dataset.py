"""Profile and index the official SuperNEMO signal/background dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import h5py
import numpy as np

FILES = {
    "0nubb": ("data_0nubb_merged.h5", 1_987_943, 1),
    "2nubb": ("data_2nubb_merged.h5", 3_284_116, 0),
    "Bi214": ("data_Bi214_merged.h5", 2_634_002, 0),
    "Tl208": ("data_Tl208_merged.h5", 2_549_143, 0),
}
REQUIRED_KEYS = (
    "ev_no",
    "E1",
    "E2",
    "tX",
    "tY",
    "tZ",
    "tR",
    "dY",
    "dZ",
    "theta",
    "phiS",
    "phiR",
    "label",
)
EVENT_FEATURES = ("E1", "E2", "dY", "dZ", "phiR")
TRACKER_FEATURES = ("tX", "tY", "tZ", "tR")
SPLIT_NAMES = ("train", "validation", "test")


def _splitmix64(values: np.ndarray) -> np.ndarray:
    mixed = values.astype(np.uint64, copy=True)
    mixed += np.uint64(0x9E3779B97F4A7C15)
    mixed = (mixed ^ (mixed >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    mixed = (mixed ^ (mixed >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return mixed ^ (mixed >> np.uint64(31))


def assign_splits(process: str, event_ids: np.ndarray) -> np.ndarray:
    """Assign composite ``(process, ev_no)`` identities to an 80/10/10 split."""
    salt = int.from_bytes(hashlib.sha256(process.encode()).digest()[:8], "little")
    buckets = _splitmix64(event_ids.astype(np.uint64) ^ np.uint64(salt)) % 10_000
    return np.where(buckets < 8_000, 0, np.where(buckets < 9_000, 1, 2)).astype(
        np.uint8
    )


def _quantiles(values: np.ndarray) -> dict[str, float]:
    levels = (0.0, 0.01, 0.1, 0.5, 0.9, 0.99, 0.999, 1.0)
    result = np.quantile(values, levels)
    return {f"q{level:g}": float(value) for level, value in zip(levels, result)}


def _sha256_array(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    return hashlib.sha256(contiguous.view(np.uint8)).hexdigest()


def profile_file(
    process: str,
    path: Path,
    expected_events: int,
    class_label: int,
    output_dir: Path,
) -> dict[str, Any]:
    started = time.perf_counter()
    with h5py.File(path, "r") as handle:
        keys = tuple(handle.keys())
        if keys != REQUIRED_KEYS:
            raise ValueError(f"{path.name} key order mismatch: {keys}")
        row_counts = {key: int(handle[key].shape[0]) for key in REQUIRED_KEYS}
        if len(set(row_counts.values())) != 1:
            raise ValueError(f"{path.name} column lengths disagree: {row_counts}")

        event_rows = np.asarray(handle["ev_no"], dtype=np.int64)
        starts = np.concatenate(
            (
                np.array([0], dtype=np.int64),
                np.flatnonzero(event_rows[1:] != event_rows[:-1]).astype(np.int64) + 1,
            )
        )
        stops = np.concatenate(
            (starts[1:], np.array([event_rows.size], dtype=np.int64))
        )
        event_ids = event_rows[starts]
        hit_counts = (stops - starts).astype(np.int32)
        if event_ids.size != expected_events:
            raise ValueError(
                f"{path.name} has {event_ids.size} events, expected {expected_events}"
            )
        if event_ids.size > 1 and np.any(event_ids[1:] <= event_ids[:-1]):
            raise ValueError(f"{path.name} event IDs are not strictly increasing")

        feature_columns: list[np.ndarray] = []
        inconsistent_features: dict[str, int] = {}
        feature_ranges: dict[str, dict[str, float]] = {}
        for key in EVENT_FEATURES:
            row_values = np.asarray(handle[key], dtype=np.float32)
            inconsistent = np.count_nonzero(
                (event_rows[1:] == event_rows[:-1])
                & ~np.isclose(row_values[1:], row_values[:-1], equal_nan=True)
            )
            inconsistent_features[key] = int(inconsistent)
            if inconsistent:
                raise ValueError(
                    f"{path.name} changes event feature {key} within an event"
                )
            event_values = row_values[starts]
            feature_columns.append(event_values)
            feature_ranges[key] = _quantiles(event_values)

        event_features = np.column_stack(feature_columns).astype(np.float32)
        energy_sum = event_features[:, 0] + event_features[:, 1]
        splits = assign_splits(process, event_ids)

        label_indices = np.linspace(
            0, event_rows.size - 1, num=min(4096, event_rows.size), dtype=np.int64
        )
        observed_labels = {
            value.decode() if isinstance(value, bytes) else str(value)
            for value in np.asarray(handle["label"])[label_indices]
        }
        if observed_labels != {process}:
            raise ValueError(
                f"{path.name} label sample disagrees with process: {observed_labels}"
            )

        tracker_ranges = {}
        for key in TRACKER_FEATURES:
            row_values = np.asarray(handle[key], dtype=np.float32)
            sample_indices = np.linspace(
                0,
                event_rows.size - 1,
                num=min(1_000_000, event_rows.size),
                dtype=np.int64,
            )
            tracker_ranges[key] = _quantiles(row_values[sample_indices])

    split_counts = {
        name: int(np.count_nonzero(splits == index))
        for index, name in enumerate(SPLIT_NAMES)
    }
    overlap_counts = {}
    for left in range(3):
        for right in range(left + 1, 3):
            overlap_counts[f"{SPLIT_NAMES[left]}__{SPLIT_NAMES[right]}"] = int(
                np.intersect1d(
                    event_ids[splits == left],
                    event_ids[splits == right],
                    assume_unique=True,
                ).size
            )
    if any(overlap_counts.values()):
        raise ValueError(f"{path.name} split overlap detected: {overlap_counts}")

    output_path = output_dir / f"{process}_event_index.npz"
    np.savez_compressed(
        output_path,
        process=np.array(process),
        class_label=np.array(class_label, dtype=np.uint8),
        event_ids=event_ids,
        row_starts=starts,
        hit_counts=hit_counts,
        event_features=event_features,
        energy_sum=energy_sum,
        splits=splits,
    )
    return {
        "process": process,
        "source_file": path.name,
        "rows": int(event_rows.size),
        "events": int(event_ids.size),
        "class_label": class_label,
        "split_counts": split_counts,
        "split_overlap_counts": overlap_counts,
        "event_id_sha256": _sha256_array(event_ids),
        "split_assignment_sha256": _sha256_array(splits),
        "hit_count": _quantiles(hit_counts),
        "event_features": feature_ranges,
        "energy_sum": _quantiles(energy_sum),
        "tracker_features_sampled": tracker_ranges,
        "inconsistent_event_feature_transitions": inconsistent_features,
        "index_file": output_path.name,
        "index_file_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "wall_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    profiles = []
    for process, (filename, expected_events, class_label) in FILES.items():
        profiles.append(
            profile_file(
                process,
                args.data_dir / filename,
                expected_events,
                class_label,
                args.output_dir,
            )
        )
    report = {
        "dataset": "zenodo:20698789",
        "split_rule": {
            "identity": "(process, ev_no)",
            "hash": "splitmix64(ev_no XOR sha256(process)[:8 little-endian])",
            "buckets": {
                "train": [0, 7999],
                "validation": [8000, 8999],
                "test": [9000, 9999],
            },
        },
        "profiles": profiles,
        "total_rows": sum(profile["rows"] for profile in profiles),
        "total_events": sum(profile["events"] for profile in profiles),
        "total_wall_seconds": sum(profile["wall_seconds"] for profile in profiles),
    }
    (args.output_dir / "dataset_profile.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
