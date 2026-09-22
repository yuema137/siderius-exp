"""The main NoPrior clock survives retries and rejects changed launch inputs."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from experiments.tidmad.main_fixed_workflow import supervisor
from experiments.tidmad.main_fixed_workflow.unit_clock import (
    UNIT_SECONDS,
    create_launch_record,
    read_launch_record,
)


def test_full_runtime_refusal_precedes_clock_and_chain(tmp_path, monkeypatch):
    from experiments.shared.data_analysis_runtime import (
        require_generated_analysis_runtime,
    )
    from experiments.tidmad.main_fixed_workflow.full_binding import FullAnalysisInputs

    unit = tmp_path / "unit"
    monkeypatch.setattr(Path, "is_mount", lambda *_: True)

    def unavailable(root, checkout, **kwargs):
        require_generated_analysis_runtime(checkout)

    monkeypatch.setattr(supervisor, "resolve_full_launch", unavailable)
    monkeypatch.setattr(
        supervisor, "_run_chain", lambda *a: pytest.fail("chain started")
    )
    with pytest.raises(ValueError, match="environment is missing"):
        supervisor.run_unit(
            root=tmp_path / "exp",
            checkout=tmp_path / "infra",
            band="0-3",
            data_dir=tmp_path / "data",
            unit_dir=unit,
            run_name="full",
            launch=True,
            full_analysis=FullAnalysisInputs(
                policy_path=tmp_path / "policy.yaml",
                policy_sha256="a" * 64,
                composition_path=tmp_path / "composition.yaml",
            ),
        )
    assert not (unit / "launch.json").exists()
    assert not (unit / "workspace").exists()


@pytest.mark.parametrize(
    "code,marker,expected", [(3, False, 3), (1, True, 3), (1, False, 1), (0, False, 0)]
)
def test_real_child_exit_preserves_permanent_halt(tmp_path, code, marker, expected):
    """Before repair a real halt child exits 3 but supervisor converts it to retryable 1."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    child = (
        "from pathlib import Path; "
        + (
            f"Path({str(workspace / '.chain_halted')!r}).write_text('{{}}'); "
            if marker
            else ""
        )
        + f"raise SystemExit({code})"
    )
    record = create_launch_record(
        tmp_path / "launch.json",
        {"command": [sys.executable, "-c", child]},
        int(time.time()),
    )
    original = (tmp_path / "launch.json").read_bytes()
    assert supervisor._run_chain(record, tmp_path) == expected
    assert (tmp_path / "launch.json").read_bytes() == original


def test_halted_workspace_never_spawns_again(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    marker = workspace / ".chain_halted"
    marker.write_text('{"reason":"run_contract_failure"}')
    record = create_launch_record(
        tmp_path / "launch.json", {"command": ["must-not-execute"]}, int(time.time())
    )
    assert supervisor._run_chain(record, tmp_path) == 3
    assert marker.read_text() == '{"reason":"run_contract_failure"}'
    assert not (tmp_path / "logs").exists()


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
        calls.append(
            (record.deadline_epoch == 1_000_000 + UNIT_SECONDS, record.started_epoch)
        )
        assert unit_dir == unit
        return 0

    monkeypatch.setattr(supervisor, "resolve_no_prior_launch", preflight)
    monkeypatch.setattr(supervisor, "_run_chain", run_chain)
    arguments = {
        "root": tmp_path / "exp",
        "checkout": tmp_path / "infra",
        "band": "0-3",
        "data_dir": tmp_path / "data",
        "unit_dir": unit,
        "run_name": "reviewed-run",
        "launch": True,
    }
    assert supervisor.run_unit(**arguments) == 0
    first_bytes = (unit / "launch.json").read_bytes()
    assert unit.stat().st_mode & 0o777 == 0o700
    assert (unit / "launch.json").stat().st_mode & 0o777 == 0o600
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
    record = create_launch_record(
        unit / "launch.json", {"command": ["bash", "chain.sh"]}, 5
    )
    assert record.deadline_epoch == 5 + UNIT_SECONDS
    with pytest.raises(FileExistsError):
        create_launch_record(unit / "launch.json", {"command": ["bash", "other.sh"]}, 6)

    monkeypatch.setattr(
        supervisor,
        "resolve_no_prior_launch",
        lambda *_, **__: {"command": ["bash", "other.sh"]},
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
    monkeypatch.setattr(
        supervisor.os, "killpg", lambda pid, sig: killed.append((pid, sig))
    )

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
    assert (tmp_path / "logs/chain.log").stat().st_mode & 0o777 == 0o600
    events = [
        json.loads(line)
        for line in (tmp_path / "events.jsonl").read_text().splitlines()
    ]
    assert [event["event"] for event in events] == ["chain_start", "deadline_stop"]


def test_child_calibration_state_is_private_per_unit_and_persists_on_resume(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A real child must not reuse the previous unit's host-wide timing cache."""
    import sys

    stale = tmp_path / "inherited-calibration"
    stale.mkdir()
    (stale / "counter").write_text("99")
    monkeypatch.setenv("SIDERIUS_CALIBRATION_DIR", str(stale))
    monkeypatch.setattr(supervisor.time, "time", lambda: 1000.0)
    child = (
        "import os; from pathlib import Path; "
        "p=Path(os.environ['SIDERIUS_CALIBRATION_DIR']); "
        "p.mkdir(parents=True,exist_ok=True); c=p/'counter'; "
        "n=int(c.read_text()) if c.exists() else 0; c.write_text(str(n+1))"
    )
    records = []
    for name in ("first", "second"):
        unit = tmp_path / name
        record = create_launch_record(
            unit / "launch.json", {"command": [sys.executable, "-c", child]}, 1000
        )
        assert supervisor._run_chain(record, unit) == 0
        records.append((record, unit))
    record, first = records[0]
    assert supervisor._run_chain(record, first) == 0
    assert (first / "calibration/counter").read_text() == "2"
    assert (records[1][1] / "calibration/counter").read_text() == "1"
    assert (stale / "counter").read_text() == "99"


def test_full_restart_keeps_clock_and_rejects_policy_or_condition_change(
    monkeypatch, tmp_path
):
    from experiments.tidmad.main_fixed_workflow.full_binding import FullAnalysisInputs

    monkeypatch.setattr(Path, "is_mount", lambda *_: True)
    now = [1000000]
    monkeypatch.setattr(supervisor.time, "time", lambda: now[0])
    checks, executions = [], []
    monkeypatch.setattr(
        supervisor,
        "_verify_execution_environment",
        lambda root, *, include_analysis=False: checks.append(include_analysis),
    )
    monkeypatch.setattr(
        supervisor,
        "_run_chain",
        lambda record, unit: executions.append(record.deadline_epoch) or 0,
    )
    monkeypatch.setattr(
        supervisor,
        "resolve_full_launch",
        lambda *args, full_analysis, **kwargs: {
            "condition": "full",
            "analysis": full_analysis.model_dump(mode="json"),
            "command": ["bash", "chain.sh"],
        },
    )
    monkeypatch.setattr(
        supervisor,
        "resolve_no_prior_launch",
        lambda *args, **kwargs: {
            "condition": "no-prior",
            "command": ["bash", "chain.sh"],
        },
    )
    binding = FullAnalysisInputs(
        policy_path=tmp_path / "policy",
        policy_sha256="a" * 64,
        composition_path=tmp_path / "composition",
    )
    unit = tmp_path / "unit"
    kwargs = {
        "root": tmp_path / "exp",
        "checkout": tmp_path / "infra",
        "band": "0-3",
        "data_dir": tmp_path / "data",
        "unit_dir": unit,
        "run_name": "full",
        "launch": True,
        "full_analysis": binding,
    }
    assert supervisor.run_unit(**kwargs) == 0
    receipt = (unit / "launch.json").read_bytes()
    now[0] += 60
    assert supervisor.run_unit(**kwargs) == 0
    assert (unit / "launch.json").read_bytes() == receipt
    assert executions == [1000000 + UNIT_SECONDS, 1000000 + UNIT_SECONDS]
    assert checks == [True, True]
    for altered in [None, binding.model_copy(update={"policy_sha256": "b" * 64})]:
        with pytest.raises(ValueError, match="differ from the recorded launch"):
            supervisor.run_unit(**{**kwargs, "full_analysis": altered})
    assert len(executions) == 2


@pytest.mark.parametrize("owner", ["exp", "infra", "data", "unit"])
def test_full_inputs_inside_managed_directories_fail_before_unit_creation(
    tmp_path, owner
):
    """A symlink must not hide an input that source/run cleanup could delete."""
    from experiments.tidmad.main_fixed_workflow.full_binding import FullAnalysisInputs

    alias = tmp_path / "external-looking.yaml"
    alias.symlink_to(tmp_path / owner / "analysis.yaml")
    binding = FullAnalysisInputs(
        policy_path=alias,
        policy_sha256="a" * 64,
        composition_path=tmp_path / "composition.yaml",
    )
    with pytest.raises(ValueError, match="outside checkouts, data and run"):
        supervisor.run_unit(
            root=tmp_path / "exp",
            checkout=tmp_path / "infra",
            band="0-3",
            data_dir=tmp_path / "data",
            unit_dir=tmp_path / "unit",
            run_name="full",
            launch=True,
            full_analysis=binding,
        )
    assert not (tmp_path / "unit").exists()


@pytest.mark.parametrize(
    "flags",
    [
        ["--condition", "full"],
        ["--analysis-policy", "policy.yaml"],
    ],
)
def test_cli_rejects_incomplete_or_no_prior_analysis_before_execution(
    monkeypatch, flags
):
    """Condition/flag mistakes must never reach the effectful supervisor."""
    import sys

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "supervisor",
            "--siderius-checkout",
            "/infra",
            "--band",
            "0-3",
            "--data_dir",
            "/data",
            "--unit-dir",
            "/unit",
            "--run_name",
            "test",
            "--launch",
            *flags,
        ],
    )
    monkeypatch.setattr(
        supervisor, "run_unit", lambda **_: pytest.fail("unexpected launch")
    )
    with pytest.raises(SystemExit) as exc:
        supervisor.main()
    assert exc.value.code == 2
