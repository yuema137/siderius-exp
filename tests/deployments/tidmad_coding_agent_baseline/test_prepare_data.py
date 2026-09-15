from __future__ import annotations

import hashlib

import h5py
import numpy as np
from deployments.tidmad_coding_agent_baseline.tools.model import (
    DEVELOPMENT_FILE_BY_BAND,
    DEVELOPMENT_FILES,
    TRAINING_FILES,
)
from deployments.tidmad_coding_agent_baseline.tools.prepare_data import prepare


def _write_raw(path, value):
    with h5py.File(path, "w") as handle:
        handle.attrs["FilePartialNumber"] = value
        handle.attrs["FileCreation"] = "private release identity"
        group = handle.require_group("timeseries")
        group.create_group("channel0001").create_dataset(
            "timeseries", data=np.array([value], dtype=np.int8)
        )
        group.create_group("channel0002").create_dataset(
            "timeseries", data=np.array([-value], dtype=np.int8)
        )


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_prepared_splits_are_disjoint_and_final_validation_stays_private(tmp_path):
    source = tmp_path / "source"
    data = tmp_path / "data"
    source.mkdir()
    data.mkdir()
    lines = []
    source_hashes = {}
    for index in range(20):
        for split in ("training", "validation"):
            name = f"abra_{split}_{index:04d}.h5"
            path = source / name
            _write_raw(path, index + 1)
            source_hashes[name] = _sha(path)
            lines.append(f"{source_hashes[name]}  {name}")
    manifest = tmp_path / "manifest.sha256"
    manifest.write_text("\n".join(lines) + "\n")

    prepare(source, data, manifest)

    assert set(TRAINING_FILES).isdisjoint(DEVELOPMENT_FILES)
    assert set(TRAINING_FILES) | set(DEVELOPMENT_FILES) == set(range(20))
    for index in TRAINING_FILES:
        assert (data / "public-training" / f"abra_training_{index:04d}.h5").is_file()
    for index in DEVELOPMENT_FILES:
        assert not (data / "public-training" / f"abra_training_{index:04d}.h5").exists()
        name = f"abra_validation_{index:04d}.h5"
        band = next(
            band for band, held_out in DEVELOPMENT_FILE_BY_BAND.items() if held_out == index
        )
        public_name = f"development-band-{band}.h5"
        with h5py.File(data / "public-development" / public_name, "r") as handle:
            assert "timeseries/channel0001" in handle
            assert "timeseries/channel0002" not in handle
            assert "FilePartialNumber" not in handle.attrs
            assert "FileCreation" not in handle.attrs
        with h5py.File(data / "private-development" / name, "r") as handle:
            assert "timeseries/channel0002" in handle
    assert not (data / "public-validation").exists()
    for index in range(20):
        name = f"abra_validation_{index:04d}.h5"
        with h5py.File(data / "private-validation-input" / name, "r") as handle:
            assert "timeseries/channel0001" in handle
            assert "timeseries/channel0002" not in handle
            assert "FilePartialNumber" not in handle.attrs
            assert "FileCreation" not in handle.attrs
        assert _sha(source / name) == source_hashes[name]
        assert _sha(data / "private-validation" / name) == source_hashes[name]
