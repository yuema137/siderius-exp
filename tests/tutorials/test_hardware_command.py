"""Hardware-only configuration projection never invokes a task or paid workflow."""

import json
from types import SimpleNamespace

import pytest

from tutorials.paper.prepared.runner import PreparedExperiment
from tutorials.paper.runner import TutorialExperiment
from tutorials.paper.tidmad.runner import TidmadExperiment
from tutorials.shared import hardware
from tutorials.shared.gpu_check import GpuCheckReport
from tutorials.supplementary.mjd.settings import MjdExperiment
from tutorials.supplementary.pet.settings import PetExperiment
from tutorials.supplementary.supernemo.settings import SuperNemoExperiment


def values(tmp_path):
    return {
        "infra_checkout": tmp_path / "infra",
        "data_dir": tmp_path / "absent data",
        "workspace": tmp_path / "new output" / "run",
        "composition": tmp_path / "absent task.yaml",
        "llm_config": tmp_path / "absent llm.json",
        "workflow": tmp_path / "absent workflow.json",
        "vram_gib": 8.0,
        "trial_vram_gib": 4.0,
        "formal_vram_gib": 10.0,
    }


@pytest.mark.parametrize(
    "model,task",
    [
        (TutorialExperiment, "tess"),
        (TidmadExperiment, "tidmad"),
        (PreparedExperiment, "project8"),
        (PreparedExperiment, "ligo"),
        (PetExperiment, "pet"),
        (MjdExperiment, "mjd"),
        (SuperNemoExperiment, "supernemo"),
    ],
)
def test_all_seven_saved_schemas_preserve_resource_override_semantics(
    tmp_path, model, task
):
    payload = {**values(tmp_path), "run_name": "demo"}
    if model is TutorialExperiment:
        payload["version"] = "siderius-tess-tutorial-v1"
    if model in (TutorialExperiment, TidmadExperiment, PreparedExperiment):
        payload.pop("workflow")
    if model is PreparedExperiment:
        payload["task"] = task
        payload["literature_config"] = tmp_path / "absent literature.yaml"
    saved = model.model_validate(payload)
    selected = hardware.HardwareSettings.model_validate_json(saved.model_dump_json())
    assert selected.infra_checkout == saved.infra_checkout
    assert selected.workspace == saved.workspace
    assert (selected.vram_gib, selected.trial_vram_gib, selected.formal_vram_gib) == (
        8,
        4,
        10,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("vram_gib", None),
        ("vram_gib", True),
        ("vram_gib", float("nan")),
        ("infra_checkout", "relative"),
        ("workspace", "relative"),
    ],
)
def test_projection_never_guesses_missing_or_invalid_resource_bindings(
    tmp_path, field, value
):
    payload = values(tmp_path)
    if value is None:
        payload.pop(field)
    else:
        payload[field] = value
    with pytest.raises(ValueError):
        hardware.HardwareSettings.model_validate(payload)


def report():
    return GpuCheckReport(
        installed_backend="cuda",
        runtime_version="synthetic",
        device_name="Any GPU",
        capacity_gib=24.0,
        device_uuid="GPU-test",
        occupied_gib=2.0,
        trial_vram_gib=4.0,
        formal_vram_gib=10.0,
        configured_cap_gib=10.0,
        effective_ceiling_gib=24.0,
        remaining_after_cap_gib=12.0,
        host_quota_gib=None,
        operator_ceiling_gib=None,
        limitations=(),
    )


def test_command_needs_no_keys_data_or_task_and_creates_no_workspace(
    tmp_path, monkeypatch, capsys
):
    selected = hardware.HardwareSettings.model_validate(values(tmp_path))
    saved = tmp_path / "saved experiment.json"
    saved.write_text(selected.model_dump_json())
    calls = []
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        hardware,
        "verify_framework_pin",
        lambda root, infra: calls.append("pin") or "a" * 40,
    )
    monkeypatch.setattr(
        hardware,
        "verify_installed_framework",
        lambda revision, root: calls.append("installed"),
    )
    monkeypatch.setattr(
        hardware, "gpu_report", lambda settings: calls.append("gpu") or report()
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["hardware", "--experiment", str(saved)])
    hardware.main()
    result = json.loads(capsys.readouterr().out)
    assert calls == ["pin", "installed", "gpu"]
    assert result["gpu"]["configured_cap_gib"] == 10
    assert "not full experiment" in result["scope"]
    assert result["host"]["job_ram_allowance"].startswith("unknown")
    assert not selected.workspace.parent.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["saved experiment.json"]


def test_bad_pair_refuses_before_hardware_or_workspace_access(tmp_path, monkeypatch):
    def refuse(*args):
        raise ValueError("wrong revision")

    monkeypatch.setattr(hardware, "verify_framework_pin", refuse)
    monkeypatch.setattr(
        hardware, "gpu_report", lambda *_: pytest.fail("GPU was touched")
    )
    monkeypatch.setattr(
        hardware, "host_observations", lambda *_: pytest.fail("Output was touched")
    )
    with pytest.raises(ValueError, match="wrong revision"):
        hardware.inspect_hardware(
            hardware.HardwareSettings.model_validate(values(tmp_path))
        )


def test_host_observation_is_not_a_job_ram_or_output_size_promise(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        hardware.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(total=100, available=20),
    )
    observed = hardware.host_observations(tmp_path / "not created" / "run")
    assert observed["host_ram"] == {"total_bytes": 100, "available_bytes": 20}
    assert observed["output_free_bytes"] > 0
    assert observed["required_output_bytes"].startswith("unknown")
    assert list(tmp_path.iterdir()) == []


def test_invalid_projection_does_not_echo_ignored_secret_values(tmp_path, monkeypatch):
    saved = tmp_path / "bad.json"
    saved.write_text(json.dumps({"api_key": "never-print-this"}))
    monkeypatch.setattr("sys.argv", ["hardware", "--experiment", str(saved)])
    with pytest.raises(ValueError, match="Invalid saved hardware settings") as error:
        hardware.main()
    assert "never-print-this" not in str(error.value)


def test_actual_saved_launch_refuses_before_native_chain_or_run_receipt(
    tmp_path, monkeypatch
):
    from tutorials.supplementary.mjd import runner

    saved = tmp_path / "experiment.json"
    selected = MjdExperiment.model_validate(values(tmp_path))
    saved.write_text(selected.model_dump_json())
    for name in ("verify_installed_framework", "selected_task", "require_credentials"):
        monkeypatch.setattr(runner, name, lambda *a: None)
    monkeypatch.setattr(runner, "build_command", lambda *a: ["bash", "never execute"])
    monkeypatch.setattr(runner, "verify_framework_pin", lambda *a: "a" * 40)
    monkeypatch.setattr(runner, "verify_planner_setup", lambda *a, **kw: None)
    monkeypatch.setattr(runner, "composition_identity", lambda *a: "b" * 64)
    monkeypatch.setattr(runner, "credential_status", lambda *a: {})
    monkeypatch.setattr(runner.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(
        runner, "verify_files", lambda *a, **kw: pytest.fail("data scan after refusal")
    )
    monkeypatch.setattr(
        runner.os, "execvpe", lambda *a: pytest.fail("native chain launched")
    )
    # Exercise the actual shared transport's refusal through the existing launch owner.
    monkeypatch.setattr(
        "tutorials.shared.runtime.gpu_report",
        lambda *a: (_ for _ in ()).throw(ValueError("insufficient headroom")),
    )
    monkeypatch.setattr("sys.argv", ["runner", "--experiment", str(saved), "--launch"])
    with pytest.raises(ValueError, match="insufficient headroom"):
        runner.main()
    assert not selected.workspace.parent.exists()
    assert not selected.workspace.with_suffix(".tutorial.json").exists()
