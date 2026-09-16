from __future__ import annotations

import hashlib

import h5py
import numpy as np

from deployments.tidmad_coding_agent_baseline.tools.model import ALL_FILE_INDICES
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


def test_all_training_is_public_and_full_validation_stays_private(tmp_path):
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

    for index in ALL_FILE_INDICES:
        assert (data / "public-training" / f"abra_training_{index:04d}.h5").is_file()
    assert not (data / "public-development").exists()
    assert not (data / "private-development").exists()
    assert not (data / "public-validation").exists()
    for index in ALL_FILE_INDICES:
        name = f"abra_validation_{index:04d}.h5"
        with h5py.File(data / "private-validation-input" / name, "r") as handle:
            assert "timeseries/channel0001" in handle
            assert "timeseries/channel0002" not in handle
            assert "FilePartialNumber" not in handle.attrs
            assert "FileCreation" not in handle.attrs
        assert _sha(source / name) == source_hashes[name]
        assert _sha(data / "private-validation" / name) == source_hashes[name]


def test_single_band_manifest_stages_only_matching_file_pairs(tmp_path):
    source = tmp_path / "source"
    data = tmp_path / "data"
    source.mkdir()
    data.mkdir()
    lines = []
    for index in range(4, 10):
        for split in ("training", "validation"):
            name = f"abra_{split}_{index:04d}.h5"
            path = source / name
            _write_raw(path, index + 1)
            lines.append(f"{_sha(path)}  {name}")
    manifest = tmp_path / "manifest.sha256"
    manifest.write_text("\n".join(lines) + "\n")
    prepare(source, data, manifest)
    assert len(list((data / "public-training").glob("*.h5"))) == 6
    assert len(list((data / "private-validation").glob("*.h5"))) == 6
    assert len(list((data / "private-validation-input").glob("*.h5"))) == 6
    assert not (data / "public-training" / "abra_training_0000.h5").exists()
