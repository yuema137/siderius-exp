"""The main NoPrior clock survives retries and rejects changed launch inputs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from experiments.tidmad.main_fixed_workflow import supervisor
from experiments.tidmad.main_fixed_workflow.unit_clock import (
    UNIT_SECONDS,
    create_launch_record,
    read_launch_record,
)


def test_no_prior_clock_is_created_once_and_reused_after_restart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    unit = tmp_path / "unit"
    calls: list[tuple[bool, int]] = []
    fresh_checks: list[bool] = []
    now = [1_000_000]
    monkeypatch.setattr(supervisor.time, "time", lambda: now[0])
    monkeypatch.setattr(Path, "is_mount", lambda *_: True)
    monkeypatch.setattr(supervisor, "_verify_execution_environment", lambda *_: None)

    def preflight(*args, require_fresh_workspace: bool, **kwargs):
        assert args == (tmp_path / "exp", tmp_path / "infra")
        fresh_checks.append(require_fresh_workspace)
        assert kwargs["workspace"] == unit / "workspace"
        return {"command": ["bash", "chain.sh"], "band": kwargs["band"]}

    def run_chain(record, unit_dir):
        calls.append((record.deadline_epoch == 1_000_000 + UNIT_SECONDS, record.started_epoch))
        assert unit_dir == unit
        return 0

    monkeypatch.setattr(supervisor, "resolve_no_prior_launch", preflight)
    monkeypatch.setattr(supervisor, "_run_chain", run_chain)
    arguments = dict(
        root=tmp_path / "exp",
        checkout=tmp_path / "infra",
        band="0-3",
        data_dir=tmp_path / "data",
        unit_dir=unit,
        run_name="reviewed-run",
        launch=True,
    )
    assert supervisor.run_unit(**arguments) == 0
    first_bytes = (unit / "launch.json").read_bytes()
    assert read_launch_record(unit / "launch.json").deadline_utc.endswith("+00:00")

    (unit / "workspace").mkdir()
    (unit / "workspace" / "existing-history").write_text("kept")
    now[0] += 60
    assert supervisor.run_unit(**arguments) == 0
    assert (unit / "launch.json").read_bytes() == first_bytes
    assert calls == [(True, 1_000_000), (True, 1_000_000)]
    assert fresh_checks == [True, False]

    now[0] += UNIT_SECONDS
    assert supervisor.run_unit(**arguments) == 0
    assert len(calls) == 2


def test_no_prior_clock_refuses_changed_inputs_and_replacement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    unit = tmp_path / "unit"
    record = create_launch_record(unit / "launch.json", {"command": ["bash", "chain.sh"]}, 5)
    assert record.deadline_epoch == 5 + UNIT_SECONDS
    with pytest.raises(FileExistsError):
        create_launch_record(unit / "launch.json", {"command": ["bash", "other.sh"]}, 6)

    monkeypatch.setattr(
        supervisor, "resolve_no_prior_launch", lambda *_, **__: {"command": ["bash", "other.sh"]}
    )
    with pytest.raises(ValueError, match="differ from the recorded launch"):
        supervisor.run_unit(
            root=tmp_path / "exp",
            checkout=tmp_path / "infra",
            band="0-3",
            data_dir=tmp_path / "data",
            unit_dir=unit,
            run_name="reviewed-run",
            launch=False,
        )
    assert read_launch_record(unit / "launch.json") == record


def test_no_prior_clock_refuses_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_text("{}")
    (tmp_path / "launch.json").symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        read_launch_record(tmp_path / "launch.json")


def test_no_prior_unit_directory_must_be_external(tmp_path: Path) -> None:
    checkout = tmp_path / "exp"
    with pytest.raises(ValueError, match="separate from checkouts and data"):
        supervisor.run_unit(
            root=checkout,
            checkout=tmp_path / "infra",
            band="0-3",
            data_dir=tmp_path / "data",
            unit_dir=checkout / "accidental-unit",
            run_name="reviewed-run",
            launch=True,
        )
    assert not (checkout / "accidental-unit").exists()


def test_no_prior_launch_refuses_unmounted_unit_parent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(Path, "is_mount", lambda *_: False)
    unit = tmp_path / "unit"
    with pytest.raises(ValueError, match="mounted persistent volume"):
        supervisor.run_unit(
            root=tmp_path / "exp",
            checkout=tmp_path / "infra",
            band="0-3",
            data_dir=tmp_path / "data",
            unit_dir=unit,
            run_name="reviewed-run",
            launch=True,
        )
    assert not unit.exists()


def test_no_prior_supervisor_kills_chain_group_at_deadline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    record = create_launch_record(
        tmp_path / "launch.json",
        {"command": ["bash", "chain.sh"]},
        1002 - UNIT_SECONDS,
    )
    monkeypatch.setattr(supervisor.time, "time", lambda: 1000.0)
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(supervisor.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    class FakeProcess:
        pid = 321
        waits = 0

        def wait(self, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise subprocess.TimeoutExpired("chain", timeout)
            return -9

    process = FakeProcess()
    monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *_, **__: process)
    assert supervisor._run_chain(record, tmp_path) == 0
    assert killed == [(321, supervisor.signal.SIGKILL)]
    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert [event["event"] for event in events] == ["chain_start", "deadline_stop"]
