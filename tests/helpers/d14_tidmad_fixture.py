"""Frozen D14 fixture recovered from SIDERIUS a715b84e.

The HDF5 payload algorithm, seeds and physical constants are preserved.
Only access to the current opaque DatasetProfile topology is adapted; the
immutable evidence checks every generated file's bytes before dataset parity.

A small Dataset Profile derived from ``TIDMAD_PROFILE`` by varying ONLY the
dataset geometry / count (`num_files`, `psd_segment_length`,
`segments_per_file`) — the Step-02 contrast-fixture pattern
(`tests/unit/execute_tools/test_step02a_c6_contrast_rungs.py`) — with BOTH
file families written to disk: ``abra_training_000i.h5`` and
``abra_validation_000i.h5`` hold DISTINCT payloads, so an R3 observed on
the validation family cannot coincide with an R2 observed on the training
family by accident.

Honestly labelled a contrast-profile fixture, NOT Track B / Track C: it is
TIDMAD-shaped (two parallel families, one index space), which is what the
production trainer reads today.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import h5py
import numpy as np
from execute_tools.dataset_config import DatasetProfile

from tasks.tidmad.runtime.profile import tidmad_topology

DEFAULT_SEG_SIZE = 1000


@dataclass(frozen=True)
class TwoFamilyFixture:
    """The written fixture: where it lives and how it is declared."""

    data_dir: str
    profile: DatasetProfile
    seg_size: int
    num_files: int
    segments_per_file: int
    ml_segs_per_psd: int
    written: dict[str, list[str]] = field(default_factory=dict)

    def full_sample_set(self) -> dict[str, list[int]]:
        """Every declared PSD segment of every declared file (string keys,
        the JSON-transport form the trainer receives)."""
        return {
            str(i): list(range(self.segments_per_file)) for i in range(self.num_files)
        }

    def training_path(self, file_index: int) -> str:
        return os.path.join(
            self.data_dir,
            tidmad_topology(self.profile).dataset.training_file_name(file_index),
        )

    def validation_path(self, file_index: int) -> str:
        return os.path.join(
            self.data_dir,
            tidmad_topology(self.profile).dataset.validation_file_name(file_index),
        )


def make_two_family_profile(
    *,
    num_files: int = 3,
    psd_segment_length: int = 2000,
    segments_per_file: int = 4,
) -> DatasetProfile:
    """``TIDMAD_PROFILE`` with only the dataset count / geometry varied.

    Built through ``model_validate`` (not ``model_copy``) so the result is
    exactly what the subprocess boundary reloads from JSON — a profile that
    only validates in-process would let a rung pass while the real child
    refuses it. The task-owned file sets (anchor / peek) are re-declared
    inside the smaller index space, as any bound task with ``num_files``
    files would declare them.
    """
    payload = {
        "partition_count": num_files,
        "topology": {
            "dataset": {
                "sampling_frequency": 10_000_000.0,
                "training_file_pattern": "abra_training_{file_index:04d}.h5",
                "validation_file_pattern": "abra_validation_{file_index:04d}.h5",
            },
            "channels": {
                "input_channel": "channel0001",
                "target_channel": "channel0002",
            },
            "encoding": {
                "storage_dtype": "int8",
                "compute_dtype": "int16",
                "value_offset": 128,
                "num_classes": 256,
            },
        },
    }
    payload["topology"]["dataset"].update(
        {
            "psd_segment_length": psd_segment_length,
            "segments_per_file": segments_per_file,
            "num_files": num_files,
        }
    )
    payload["anchor_selection_files"] = list(range(min(num_files, 3)))
    payload["health_peek_files"] = list(range(min(num_files, 3)))
    return DatasetProfile.model_validate(payload)


def _write_file(path: str, profile: DatasetProfile, n_samples: int, seed: int) -> None:
    topology = tidmad_topology(profile)
    ch, enc = topology.channels, topology.encoding
    rng = np.random.default_rng(seed)
    a = rng.integers(-128, 127, size=n_samples).astype(enc.storage_dtype)
    b = rng.integers(-128, 127, size=n_samples).astype(enc.storage_dtype)
    with h5py.File(path, "w") as f:
        ts = f.create_group("timeseries")
        ts.create_group(ch.input_channel).create_dataset("timeseries", data=a)
        ts.create_group(ch.target_channel).create_dataset("timeseries", data=b)


def write_two_family_fixture(
    tmp_path,
    *,
    num_files: int = 3,
    psd_segment_length: int = 2000,
    segments_per_file: int = 4,
    seg_size: int = DEFAULT_SEG_SIZE,
    families: tuple[str, ...] = ("training", "validation"),
) -> TwoFamilyFixture:
    """Write the fixture under ``tmp_path`` and return its description.

    Each family / file gets its own deterministic seed
    (``1000 * family_salt + file_index``), so payloads are distinct across
    families AND across files, and identical across test runs.
    """
    profile = make_two_family_profile(
        num_files=num_files,
        psd_segment_length=psd_segment_length,
        segments_per_file=segments_per_file,
    )
    data_dir = str(tmp_path)
    n_samples = psd_segment_length * segments_per_file
    written: dict[str, list[str]] = {}
    for family in families:
        salt = 1 if family == "training" else 2
        names: list[str] = []
        for i in range(num_files):
            name = (
                tidmad_topology(profile).dataset.training_file_name(i)
                if family == "training"
                else tidmad_topology(profile).dataset.validation_file_name(i)
            )
            _write_file(
                os.path.join(data_dir, name), profile, n_samples, 1000 * salt + i
            )
            names.append(name)
        written[family] = names
    return TwoFamilyFixture(
        data_dir=data_dir,
        profile=profile,
        seg_size=seg_size,
        num_files=num_files,
        segments_per_file=segments_per_file,
        ml_segs_per_psd=psd_segment_length // seg_size,
        written=written,
    )
