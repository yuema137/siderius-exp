"""NoPrior artifact backup preserves certified models and stops at low disk space."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from experiments.tidmad.main_fixed_workflow import backup
from experiments.tidmad.main_fixed_workflow.unit_clock import create_launch_record


def _unit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    unit = tmp_path / "f-noprior-0-3-unit"
    (unit / "workspace/trained_model_artifacts/blobs").mkdir(parents=True)
    (unit / "workspace/trained_model_artifacts/blobs/known.pt").write_bytes(b"weights")
    (unit / "workspace/old.pth").write_bytes(b"retired original")
    create_launch_record(unit / "launch.json", {"workspace": str(unit / "workspace")}, 1_000_000)
    monkeypatch.setattr(Path, "is_mount", lambda path: path == tmp_path)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    return unit


def _call(unit: Path) -> dict[str, object]:
    return backup.backup_unit(
        unit_dir=unit,
        bucket="tidmad-f-noprior-0-3-a7f3",
        prefix="f-noprior-0-3/run-1",
        endpoint="https://storage.eu-north1.nebius.cloud",
        instance="f-noprior-0-3",
    )


def test_backup_sync_is_additive_and_includes_certified_checkpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    unit = _unit(monkeypatch, tmp_path)
    calls: list[list[str]] = []
    monkeypatch.setattr(backup.shutil, "disk_usage", lambda _: SimpleNamespace(free=200 * 1024**3))

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(backup.subprocess, "run", run)
    receipt = _call(unit)
    assert receipt["certified_checkpoint_count"] == 1
    assert receipt["returncode"] == 0
    assert len(calls) == 1
    command = calls[0]
    assert command[:4] == ["aws", "--endpoint-url", "https://storage.eu-north1.nebius.cloud", "s3"]
    assert "sync" in command and "--no-follow-symlinks" in command
    assert "--delete" not in command
    assert "*.pth" in command and "*.h5" in command
    assert "*.pt" not in command
    rows = [json.loads(line) for line in (unit / "backup_receipts.jsonl").read_text().splitlines()]
    assert [row["event"] for row in rows] == ["backup_sync"]


def test_low_space_stops_chain_before_sync(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    unit = _unit(monkeypatch, tmp_path)
    calls: list[list[str]] = []
    monkeypatch.setattr(backup.shutil, "disk_usage", lambda _: SimpleNamespace(free=40 * 1024**3))

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(backup.subprocess, "run", run)
    _call(unit)
    assert calls[0] == ["systemctl", "stop", "tidmad-no-prior@f-noprior-0-3.service"]
    assert calls[1][0] == "aws"
    rows = [json.loads(line) for line in (unit / "backup_receipts.jsonl").read_text().splitlines()]
    assert [row["event"] for row in rows] == ["low_space_stop", "backup_sync"]


def test_backup_requires_launch_receipt_and_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    unit = tmp_path / "f-noprior-0-3-unit"
    unit.mkdir()
    monkeypatch.setattr(Path, "is_mount", lambda path: path == tmp_path)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-id")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    with pytest.raises(ValueError, match="launch receipt"):
        _call(unit)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY")
    with pytest.raises(ValueError, match="credentials are absent"):
        _call(unit)


def test_disk_guard_does_not_need_backup_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    unit = _unit(monkeypatch, tmp_path)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID")
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY")
    monkeypatch.setattr(backup.shutil, "disk_usage", lambda _: SimpleNamespace(free=80 * 1024**3))

    def unexpected(*args, **kwargs):
        raise AssertionError("healthy disk guard must not invoke external commands")

    monkeypatch.setattr(backup.subprocess, "run", unexpected)
    assert backup.check_space(unit_dir=unit, instance="f-noprior-0-3") == 80 * 1024**3
