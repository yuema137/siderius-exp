"""TIDMAD loader parity for task-owned dataset-profile fields.

SIDERIUS owns the generic JSON/argv transport. This external witness owns the
scientific file family, channel, encoding, and class-alphabet declarations that
the indexed TIDMAD compatibility loader must consume while it remains supported.
"""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np

import execute_tools.train_engine_sandbox as train_engine
from execute_tools.dataset_config import DatasetProfile, ValueEncoding
from tasks.tidmad.runtime.profile import tidmad_topology

TASK_ROOT = Path(__file__).resolve().parents[3] / "tasks" / "tidmad"
TASK_PROFILE = DatasetProfile.model_validate_json(
    (TASK_ROOT / "resolved" / "dataset_profile.json").read_text(encoding="utf-8")
)
SEG_SIZE = 8
ML_PER_PSD = 2
PSD_LENGTH = SEG_SIZE * ML_PER_PSD
PSD_COUNT = 2


def _profile(**dataset_overrides) -> DatasetProfile:
    payload = TASK_PROFILE.to_wire()
    payload["dataset"].update(
        {"psd_segment_length": PSD_LENGTH, "num_files": 5, **dataset_overrides}
    )
    payload["anchor_selection_files"] = [0, 2, 4]
    payload["health_peek_files"] = [1, 3]
    return DatasetProfile.model_validate(payload)


def _write_h5(path: Path, channels: tuple[str, str]) -> tuple[np.ndarray, np.ndarray]:
    count = PSD_LENGTH * PSD_COUNT
    input_values = (np.arange(count, dtype=np.int64) % 251 - 125).astype(np.int8)
    target_values = ((np.arange(count, dtype=np.int64) * 7 + 3) % 251 - 125).astype(
        np.int8
    )
    with h5py.File(path, "w") as handle:
        timeseries = handle.create_group("timeseries")
        timeseries.create_group(channels[0]).create_dataset(
            "timeseries", data=input_values
        )
        timeseries.create_group(channels[1]).create_dataset(
            "timeseries", data=target_values
        )
    return input_values, target_values


def _rows(payload: np.ndarray, psd_indices: list[int]) -> np.ndarray:
    return np.concatenate(
        [
            payload[index * PSD_LENGTH : (index + 1) * PSD_LENGTH].reshape(
                ML_PER_PSD, SEG_SIZE
            )
            for index in psd_indices
        ],
        axis=0,
    )


def test_file_names_come_from_the_task_profile(tmp_path, capsys) -> None:
    profile = _profile(training_file_pattern="run_{file_index:02d}.bin")
    train_engine.TIDMADDataset(
        str(tmp_path),
        [],
        segmentation_size=SEG_SIZE,
        sample_set={"4": [0]},
        profile=profile,
    )
    output = capsys.readouterr().out
    assert "run_04.bin" in output
    assert "abra_training_" not in output


def test_geometry_comes_from_the_task_profile(tmp_path) -> None:
    profile = _profile()
    name = tidmad_topology(profile).dataset.training_file_name(4)
    channels = tidmad_topology(profile).channels
    _write_h5(tmp_path / name, (channels.input_channel, channels.target_channel))
    dataset = train_engine.TIDMADDataset(
        str(tmp_path),
        [],
        segmentation_size=SEG_SIZE,
        sample_set={"4": [0, 1]},
        profile=profile,
    )
    assert len(dataset) == PSD_COUNT * ML_PER_PSD


def test_channel_identity_comes_from_the_task_profile(tmp_path) -> None:
    payload = _profile().to_wire()
    payload["channels"] = {
        "input_channel": "sensor_raw",
        "target_channel": "sensor_clean",
    }
    profile = DatasetProfile.model_validate(payload)
    name = tidmad_topology(profile).dataset.training_file_name(4)
    input_values, target_values = _write_h5(
        tmp_path / name, ("sensor_raw", "sensor_clean")
    )
    dataset = train_engine.TIDMADDataset(
        str(tmp_path),
        [],
        segmentation_size=SEG_SIZE,
        sample_set={"4": [0]},
        profile=profile,
    )
    np.testing.assert_array_equal(dataset.idict[name], _rows(input_values, [0]))
    np.testing.assert_array_equal(dataset.tdict[name], _rows(target_values, [0]))


def test_encoding_offset_comes_from_the_task_profile(tmp_path) -> None:
    base = _profile()
    topology = tidmad_topology(base)
    name = topology.dataset.training_file_name(4)
    input_values, _ = _write_h5(
        tmp_path / name,
        (topology.channels.input_channel, topology.channels.target_channel),
    )
    payload = base.to_wire()
    payload["encoding"] = ValueEncoding(
        storage_dtype="int8",
        compute_dtype="int16",
        value_offset=200,
        num_classes=400,
    ).model_dump()
    shifted = DatasetProfile.model_validate(payload)
    default_values = train_engine.TIDMADDataset(
        str(tmp_path),
        [],
        segmentation_size=SEG_SIZE,
        sample_set={"4": [0]},
        profile=base,
    )[0][0]
    shifted_values = train_engine.TIDMADDataset(
        str(tmp_path),
        [],
        segmentation_size=SEG_SIZE,
        sample_set={"4": [0]},
        profile=shifted,
    )[0][0]
    expected = _rows(input_values, [0])[0].astype(np.int16)
    np.testing.assert_array_equal(default_values, expected + 128)
    np.testing.assert_array_equal(shifted_values, expected + 200)


def test_class_alphabet_comes_from_the_task_profile(tmp_path) -> None:
    base = _profile()
    topology = tidmad_topology(base)
    name = topology.dataset.training_file_name(4)
    _write_h5(
        tmp_path / name,
        (topology.channels.input_channel, topology.channels.target_channel),
    )
    payload = base.to_wire()
    payload["encoding"]["num_classes"] = 512
    wide = DatasetProfile.model_validate(payload)
    dataset = train_engine.TIDMADDataset(
        str(tmp_path),
        [],
        segmentation_size=SEG_SIZE,
        sample_set={"4": [0]},
        profile=wide,
    )
    assert dataset.class_count.shape == (512,)
