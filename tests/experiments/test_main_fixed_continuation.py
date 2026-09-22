"""A reviewed continuation preserves completed science and charges elapsed time."""

import json
import sys
import time

import pytest

from experiments.tidmad.main_fixed_workflow import continuation as c
from experiments.tidmad.main_fixed_workflow.supervisor import _run_chain
from experiments.tidmad.main_fixed_workflow.unit_clock import (
    ContinuationRecord,
    create_launch_record,
    publish_continuation,
)


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    (tmp_path / ".supervisor.lock").touch()
    (tmp_path / "workspace").mkdir()
    prior = {
        "data": {"band": "15-19"},
        "data_dir": "/data",
        "run_name": "same",
        "repository_revision": "old-exp",
        "siderius_revision": "old-infra",
        "command": ["unchanged-command"],
        "workflow_sha256": "frozen",
    }
    create_launch_record(tmp_path / "launch.json", prior, 100000)
    (tmp_path / "events.jsonl").write_text(
        json.dumps({"event": "chain_exit", "returncode": 3, "ended_epoch": 145554})
        + "\n"
    )
    evidence = tmp_path / "verified-recovery.json"
    evidence.write_text('{"verified":true}')
    current = {
        **prior,
        "repository_revision": "new-exp",
        "siderius_revision": "new-infra",
    }
    monkeypatch.setattr(c, "resolve_no_prior_launch", lambda *a, **kw: current)
    monkeypatch.setattr(c, "_verify_execution_environment", lambda *a, **kw: None)
    monkeypatch.setattr(c.Path, "is_mount", lambda *a: True)
    monkeypatch.setattr(c.time, "time", lambda: 200000)
    seen = []
    monkeypatch.setattr(c, "_run_chain", lambda record, unit: seen.append(record) or 0)
    return (
        {
            "root": tmp_path,
            "checkout": tmp_path,
            "unit": tmp_path,
            "stopped_epoch": 145554,
            "evidence": evidence,
            "launch": True,
        },
        current,
        seen,
    )


def test_resume_deducts_elapsed_and_never_resets_clock(recovery, monkeypatch):
    args, _, seen = recovery
    original = (args["unit"] / "launch.json").read_bytes()
    c.run_continuation(**args)
    assert seen[0].deadline_epoch == 240846
    receipt = (args["unit"] / "continuation.json").read_bytes()
    monkeypatch.setattr(c.time, "time", lambda: 201000)
    c.run_continuation(**args)
    assert seen[1] == seen[0]
    assert (args["unit"] / "launch.json").read_bytes() == original
    assert (args["unit"] / "continuation.json").read_bytes() == receipt


@pytest.mark.parametrize(
    "failure", ["science", "failure-time", "halt", "evidence", "revision"]
)
def test_refuses_changed_or_unreviewed_continuation(recovery, failure):
    args, current, seen = recovery
    if failure in ("evidence", "revision"):
        c.run_continuation(**args)
        seen.clear()
    if failure == "science":
        current["workflow_sha256"] = "changed"
    elif failure == "failure-time":
        args["stopped_epoch"] += 1
    elif failure == "halt":
        (args["unit"] / "workspace/.chain_halted").write_text("{}")
    elif failure == "evidence":
        args["evidence"].write_text("changed")
    else:
        current["siderius_revision"] = "third-revision"
    with pytest.raises(ValueError):
        c.run_continuation(**args)
    assert not seen


def test_preview_does_not_start_clock(recovery):
    args, _, seen = recovery
    c.run_continuation(**{**args, "launch": False})
    assert not seen
    assert not (args["unit"] / "continuation.json").exists()


def test_full_runtime_refusal_preserves_original_clock_and_results(
    recovery, monkeypatch
):
    args, _, seen = recovery
    path = args["unit"] / "launch.json"
    data = json.loads(path.read_text())
    data["preflight"]["analysis_binding"] = {
        "analysis_policy_path": "/external/policy.yaml",
        "analysis_policy_sha256": "a" * 64,
        "composition_path": "/external/composition.yaml",
    }
    path.write_text(json.dumps(data))
    original = path.read_bytes()
    result = args["unit"] / "workspace/completed-science.json"
    result.write_text('{"score":1.0}')

    def unavailable(*a, **kw):
        raise ValueError("Data Analysis generated-code runtime is unavailable")

    monkeypatch.setattr(c, "resolve_full_launch", unavailable)
    with pytest.raises(ValueError, match="generated-code runtime is unavailable"):
        c.run_continuation(**args)
    assert path.read_bytes() == original
    assert result.read_text() == '{"score":1.0}'
    assert not (args["unit"] / "continuation.json").exists()
    assert not seen


def test_full_analysis_binding_is_reused(recovery, monkeypatch):
    args, current, seen = recovery
    binding = {
        "analysis_policy_path": "/external/policy.yaml",
        "analysis_policy_sha256": "a" * 64,
        "composition_path": "/external/composition.yaml",
    }
    path = args["unit"] / "launch.json"
    payload = json.loads(path.read_text())
    payload["preflight"]["analysis_binding"] = binding
    path.write_text(json.dumps(payload))
    current["analysis_binding"] = binding
    observed = []

    def resolve(*a, full_analysis, **kw):
        assert str(full_analysis.policy_path) == binding["analysis_policy_path"]
        assert kw["require_fresh_workspace"] is False
        return current

    monkeypatch.setattr(c, "resolve_full_launch", resolve)
    monkeypatch.setattr(
        c,
        "_verify_execution_environment",
        lambda *a, include_analysis: observed.append(include_analysis),
    )
    c.run_continuation(**args)
    assert observed == [True]
    assert len(seen) == 1


def test_real_child_is_stopped_at_remaining_deadline(tmp_path):
    now = int(time.time())
    record = ContinuationRecord(
        version="tidmad-main-fixed-continuation-v1",
        original_launch_sha256="a" * 64,
        original_started_epoch=now - 86400,
        stopped_epoch=now - 1,
        started_epoch=now,
        deadline_epoch=now + 1,
        recovery_evidence_sha256="b" * 64,
        preflight={"command": [sys.executable, "-c", "import time; time.sleep(60)"]},
    )
    publish_continuation(tmp_path / "continuation.json", record)
    with pytest.raises(FileExistsError):
        publish_continuation(tmp_path / "continuation.json", record)
    started = time.monotonic()
    assert _run_chain(record, tmp_path) == 0
    assert time.monotonic() - started < 5
    assert '"event": "deadline_stop"' in (tmp_path / "events.jsonl").read_text()


def test_invalid_budget_cannot_be_constructed():
    with pytest.raises(ValueError, match="deduct"):
        ContinuationRecord(
            version="tidmad-main-fixed-continuation-v1",
            original_launch_sha256="a" * 64,
            original_started_epoch=100000,
            stopped_epoch=145554,
            started_epoch=200000,
            deadline_epoch=286400,
            recovery_evidence_sha256="b" * 64,
            preflight={},
        )
