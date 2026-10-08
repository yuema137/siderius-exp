"""Behavioral parity at the extracted saved-script lifecycle boundary."""

import json
import signal
import subprocess
from types import SimpleNamespace

import pytest

from tutorials.shared import saved_run, saved_script
from tutorials.supplementary.pet import demo
from tutorials.supplementary.pet.project import create_project
from tutorials.supplementary.pet.settings import PetExperiment


@pytest.mark.parametrize("code", [0, 7])
def test_pet_delegation_keeps_readiness_launch_and_receipt_order(
    tmp_path, monkeypatch, code
):
    """Catch premature credential/log effects or losing nonzero completion evidence."""
    project = tmp_path / "project with spaces"
    experiment = create_project(project, tmp_path / "infra", tmp_path / "images")
    script = project / "scripts/run-pet.sh"
    settings = PetExperiment.model_validate_json(experiment.read_text())
    workspace = settings.workspace
    receipt = workspace.with_suffix(".notebook-run.json")
    log = workspace.with_suffix(".console.log")
    events = []
    original_validate, original_digest = demo.validate_launcher, demo.input_digest

    def validate(*args):
        events.append("bindings")
        original_validate(*args)

    def digest(*args):
        events.append("digest")
        return original_digest(*args)

    def ready(config):
        events.append("ready")
        assert config == settings.llm_config
        assert not log.exists() and not receipt.exists()

    def launch(argv, **kwargs):
        events.append("launch")
        assert argv == ["bash", str(script), "--launch"]
        assert kwargs["start_new_session"] is True
        assert kwargs["stderr"] == subprocess.STDOUT
        assert kwargs["stdout"].name == str(log)
        assert log.is_file() and not receipt.exists()
        workspace.mkdir()
        return SimpleNamespace(wait=wait)

    def wait(*, timeout):
        events.append("wait")
        assert 0 < timeout <= 30
        assert not receipt.exists()
        return code

    monkeypatch.setattr(demo, "validate_launcher", validate)
    monkeypatch.setattr(demo, "input_digest", digest)
    monkeypatch.setattr("tutorials.supplementary.pet.runner.require_credentials", ready)
    monkeypatch.setattr(saved_run.subprocess, "Popen", launch)
    if code:
        with pytest.raises(RuntimeError, match="Saved script exited 7"):
            demo.run_demo(experiment, script)
    else:
        result = demo.run_demo(experiment, script)
        assert result == json.loads(receipt.read_text())
    recorded = receipt.read_bytes()
    result = json.loads(recorded)
    assert set(result) == {
        "input_sha256",
        "exit_code",
        "elapsed_seconds",
        "workspace",
        "log",
    }
    assert result["exit_code"] == code
    assert result["workspace"] == str(workspace) and result["log"] == str(log)
    assert result["input_sha256"] == original_digest(experiment, script)
    assert result["elapsed_seconds"] >= 0
    assert events == ["bindings", "digest", "ready", "launch", "wait"]
    events.clear()
    if code:
        with pytest.raises(RuntimeError, match="Previous script run failed"):
            demo.run_demo(experiment, script)
    else:
        assert demo.run_demo(experiment, script) == result
    assert events == ["bindings", "digest"]
    assert receipt.read_bytes() == recorded


@pytest.mark.parametrize(
    "state,message",
    [
        ("changed", "Inputs changed"),
        ("missing", "Completed workspace is missing"),
        ("workspace", "Existing or interrupted"),
        ("log", "Existing or interrupted"),
    ],
)
def test_refusals_precede_readiness_and_preserve_files(
    tmp_path, monkeypatch, state, message
):
    """Catch a cache refusal becoming an automatic launch or destructive cleanup."""
    workspace = tmp_path / "runs/example"
    workspace.parent.mkdir()
    receipt = workspace.with_suffix(".notebook-run.json")
    log = workspace.with_suffix(".console.log")
    if state in {"changed", "missing"}:
        receipt.write_text(
            json.dumps(
                {
                    "input_sha256": "old" if state == "changed" else "same",
                    "exit_code": 0,
                }
            )
        )
    if state in {"changed", "workspace"}:
        workspace.mkdir()
    if state == "log":
        log.write_text("interrupted evidence")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        pytest.fail("refused run crossed readiness/launch boundary")

    monkeypatch.setattr(saved_run.subprocess, "Popen", forbidden)
    with pytest.raises(ValueError, match=message):
        saved_run.run_saved_script(
            script=tmp_path / "saved.sh",
            workspace=workspace,
            digest="same",
            ready=forbidden,
            timeout_seconds=10,
        )
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_interrupt_captures_descendants_before_signals_and_retains_only_log(
    tmp_path, monkeypatch
):
    """Catch extraction weakening interrupt propagation or detached-worker escalation."""
    events = []
    process = SimpleNamespace(pid=12345)
    waits = iter([KeyboardInterrupt(), subprocess.TimeoutExpired("bash", 5), 0])

    def wait(timeout=None):
        events.append(("wait", timeout))
        outcome = next(waits)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    process.wait = wait
    child = SimpleNamespace(
        terminate=lambda: events.append("terminate-child"),
        kill=lambda: events.append("kill-child"),
    )

    def descendants(*, recursive):
        assert recursive is True
        events.append("capture-descendants")
        return [child]

    def wait_children(children, *, timeout):
        assert children == [child] and timeout == 5
        events.append("wait-children")
        return [], [child]

    monkeypatch.setattr(saved_run.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(
        saved_run.psutil, "Process", lambda pid: SimpleNamespace(children=descendants)
    )
    monkeypatch.setattr(saved_run.psutil, "wait_procs", wait_children)
    monkeypatch.setattr(
        saved_run.os, "killpg", lambda pid, sig: events.append(("signal", pid, sig))
    )
    monkeypatch.setattr(saved_run.time, "monotonic", lambda: 100)
    workspace = tmp_path / "runs/interrupted"
    with pytest.raises(KeyboardInterrupt):
        saved_run.run_saved_script(
            script=tmp_path / "saved.sh",
            workspace=workspace,
            digest="same",
            ready=lambda: events.append("ready"),
            timeout_seconds=60,
        )
    assert events == [
        "ready",
        ("wait", 30),
        "capture-descendants",
        ("signal", 12345, signal.SIGTERM),
        "terminate-child",
        "wait-children",
        "kill-child",
        ("wait", 5),
        ("signal", 12345, signal.SIGKILL),
        ("wait", None),
    ]
    assert workspace.with_suffix(".console.log").is_file()
    assert not workspace.with_suffix(".notebook-run.json").exists()


def test_shared_launcher_binds_supplied_runner_and_quoted_paths(tmp_path):
    """Catch the shared writer retaining Pet's runner or losing spaces in bindings."""
    script = tmp_path / "saved script.sh"
    experiment = tmp_path / "saved experiment.json"
    checkout = tmp_path / "exp checkout"
    module = "tutorials.example.runner"
    saved_script.write_launcher(
        script, experiment, checkout=checkout, runner_module=module
    )
    saved_script.validate_launcher(
        experiment, script, checkout=checkout, runner_module=module
    )
    subprocess.run(["bash", "-n", str(script)], check=True)
    assert script.stat().st_mode & 0o777 == 0o755
    before = script.read_bytes()
    with pytest.raises(FileExistsError):
        saved_script.write_launcher(
            script, experiment, checkout=checkout, runner_module=module
        )
    assert script.read_bytes() == before
    with pytest.raises(ValueError, match="selected tutorial runner"):
        saved_script.validate_launcher(
            experiment,
            script,
            checkout=checkout,
            runner_module="tutorials.other.runner",
        )
