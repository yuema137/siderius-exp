"""Preparation identity and failure tests using explicit synthetic hit files."""

import hashlib
import json
import subprocess
from pathlib import Path

import h5py
import numpy as np
import pytest

from tasks.supernemo_signal_background.tools import profile_dataset
from tutorials.supplementary.supernemo import prepare as prep


@pytest.fixture
def fixture_data(tmp_path, monkeypatch):
    raw = tmp_path / "raw input"
    raw.mkdir()
    files = {}
    for process in prep.PROCESSES:
        name = f"data_{process}_merged.h5"
        path = raw / name
        with h5py.File(path, "w", track_order=True) as handle:
            for key in profile_dataset.REQUIRED_KEYS:
                if key == "ev_no":
                    values = np.repeat(np.arange(40, dtype=np.int64), 2)
                elif key == "label":
                    values = np.array([process.encode()] * 80)
                else:
                    values = np.full(80, 100.0, dtype=np.float32)
                handle[key] = values
        files[name] = {
            "bytes": path.stat().st_size,
            "md5": hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest(),
        }
    manifest = tmp_path / "fixture-source.json"
    manifest.write_text(
        json.dumps({"record": 20698789, "doi": "fixture-only", "files": files})
    )
    monkeypatch.setattr(prep, "SOURCE_MANIFEST", manifest)
    calls = []

    def synthetic_profile(command, **kwargs):
        # Exercise the actual scientific profiler, with explicitly smaller fixture counts.
        assert command[2] == str(prep.PROFILER)
        assert kwargs == {"check": True}
        output = Path(command[command.index("--output-dir") + 1])
        data = Path(command[command.index("--data-dir") + 1])
        profiles = []
        for process in prep.PROCESSES:
            profiles.append(
                profile_dataset.profile_file(
                    process,
                    data / f"data_{process}_merged.h5",
                    40,
                    int(process == "0nubb"),
                    output,
                )
            )
        (output / "dataset_profile.json").write_text(json.dumps({"profiles": profiles}))
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(prep.subprocess, "run", synthetic_profile)
    return raw, tmp_path / "prepared root", calls


def test_preparation_preserves_sources_and_reuses_unchanged_scientific_tool(
    fixture_data,
):
    raw, output, calls = fixture_data
    before = {p.name: prep.digest(p) for p in raw.iterdir()}
    prep.prepare(raw, output)
    receipt = prep.verify_prepared(output, hashes=True)
    assert len(calls) == 1 and len(receipt.generated_sha256) == 5
    assert all((output / name).is_symlink() for name in before)
    assert before == {p.name: prep.digest(p) for p in raw.iterdir()}
    for process in prep.PROCESSES:
        with np.load(output / f"event_indexes/{process}_event_index.npz") as index:
            assert len(index["event_ids"]) == 40
            assert np.array_equal(index["hit_counts"], np.full(40, 2))
            assert np.array_equal(
                index["splits"],
                profile_dataset.assign_splits(process, index["event_ids"]),
            )
    with pytest.raises(ValueError, match="new preparation directory"):
        prep.prepare(raw, output)


@pytest.mark.parametrize(
    "changed", ["index", "report", "raw_binding", "profiler", "manifest"]
)
def test_modified_preparation_refuses_reuse(
    fixture_data, monkeypatch, changed, tmp_path
):
    raw, output, _ = fixture_data
    prep.prepare(raw, output)
    if changed == "index":
        with (output / "event_indexes/0nubb_event_index.npz").open("ab") as stream:
            stream.write(b"changed")
    elif changed == "report":
        (output / "event_indexes/dataset_profile.json").write_text("{}")
    elif changed == "raw_binding":
        alias = tmp_path / "other-source.h5"
        alias.write_bytes((raw / "data_0nubb_merged.h5").read_bytes())
        (output / "data_0nubb_merged.h5").unlink()
        (output / "data_0nubb_merged.h5").symlink_to(alias)
    elif changed == "profiler":
        tool = tmp_path / "modified_profiler.py"
        tool.write_text("different scientific source")
        monkeypatch.setattr(prep, "PROFILER", tool)
    else:
        manifest = json.loads(prep.SOURCE_MANIFEST.read_text())
        manifest["doi"] = "changed"
        prep.SOURCE_MANIFEST.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="changed"):
        prep.verify_prepared(output)


def test_failed_profiler_never_publishes_ready_receipt(fixture_data, monkeypatch):
    raw, output, _ = fixture_data

    def fail(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(prep.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        prep.prepare(raw, output)
    assert (output / ".incomplete").exists() and not (output / prep.RECEIPT).exists()
    with pytest.raises(ValueError, match="Incomplete"):
        prep.verify_prepared(output)


def test_corrupt_raw_bytes_fail_before_preparation_effects(fixture_data):
    raw, output, calls = fixture_data
    path = raw / "data_0nubb_merged.h5"
    contents = bytearray(path.read_bytes())
    contents[-1] ^= 1
    path.write_bytes(contents)
    with pytest.raises(ValueError, match="Official MD5 differs"):
        prep.prepare(raw, output)
    assert not output.exists() and not calls
