"""No budget reset on resume; data checks fail before a campaign clock."""

import hashlib
import json
from pathlib import Path

import pytest

from experiments.shared.fixed_unit_clock import LaunchRecord, create_clock, read_clock
from experiments.shared.prepared_unit_preflight import verify_prepared_arrays


@pytest.mark.parametrize("seconds", [12 * 3600, 24 * 3600])
def test_clock_is_write_once_and_resume_does_not_extend_it(tmp_path, seconds):
    path = tmp_path / "launch.json"
    original = create_clock(path, preflight={"campaign_seconds": seconds}, started=100)
    with pytest.raises(FileExistsError):
        create_clock(path, preflight={"campaign_seconds": seconds}, started=500)
    resumed = read_clock(path)
    assert resumed == original
    assert resumed.deadline_epoch == 100 + seconds
    assert list(tmp_path.glob(".launch-*")) == []


def test_clock_refuses_changed_budget_or_symlink(tmp_path):
    with pytest.raises(ValueError, match="span"):
        LaunchRecord(
            started_epoch=10,
            deadline_epoch=30,
            budget_seconds=40,
            preflight={"campaign_seconds": 40},
        )
    with pytest.raises(ValueError, match="frozen preflight"):
        LaunchRecord(
            started_epoch=10,
            deadline_epoch=30,
            budget_seconds=20,
            preflight={"campaign_seconds": 40},
        )
    real = tmp_path / "clock"
    create_clock(real, preflight={"campaign_seconds": 20}, started=10)
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(ValueError, match="symlink"):
        read_clock(link)


def make_manifest(root: Path):
    artifacts = []
    for name in (
        "training/inputs.npy",
        "training/targets.npy",
        "evaluator/validation/inputs.npy",
        "evaluator/validation/targets.npy",
        "evaluator/validation/loss_indices.npy",
    ):
        path = root / name
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(b"checksum fixture")
        path.chmod(0o444)
        artifacts.append(
            {
                "path": name,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"artifacts": artifacts}))
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def test_all_arrays_are_verified_against_pinned_manifest(tmp_path):
    digest = make_manifest(tmp_path)
    receipt = verify_prepared_arrays(tmp_path, digest)
    assert len(receipt["arrays"]) == 5
    path = tmp_path / "training/inputs.npy"
    path.chmod(0o644)
    with pytest.raises(ValueError, match="writable"):
        verify_prepared_arrays(tmp_path, digest)
    path.write_bytes(b"checksum fixturX")
    path.chmod(0o444)
    with pytest.raises(ValueError, match="checksum"):
        verify_prepared_arrays(tmp_path, digest)


def test_manifest_and_population_changes_are_refused(tmp_path):
    digest = make_manifest(tmp_path)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["artifacts"].pop()
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="pinned"):
        verify_prepared_arrays(tmp_path, digest)
    with pytest.raises(ValueError, match="five"):
        verify_prepared_arrays(tmp_path, hashlib.sha256(path.read_bytes()).hexdigest())
