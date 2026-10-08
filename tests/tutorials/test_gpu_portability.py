"""Selected-device setup refuses before kernels and never borrows a framework."""

import json
import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace

import core.hardware_context as hardware
import core.runtime_control.gpu_accounting as accounting
import pytest

from tutorials.paper.runner import TutorialExperiment
from tutorials.shared import gpu_check, runtime
from tutorials.supplementary.pet.settings import PetExperiment


@pytest.fixture
def native(monkeypatch):
    context = hardware.HardwareContext(
        device_name="Arbitrary NVIDIA device",
        total_memory_bytes=192 * 1024**3,
        compute_capability=(9, 0),
        multiprocessor_count=128,
        torch_version="synthetic",
        hostname="synthetic",
        device_available=True,
        discovered_at=datetime(2026, 10, 8, tzinfo=UTC),
        visible_device_count=1,
        active_device_uuid="GPU-example",
        hardware_fingerprint_version=2,
        devices=[
            hardware.GpuDeviceProvenance(
                logical_index=0,
                name="Arbitrary NVIDIA device",
                total_memory_bytes=192 * 1024**3,
                compute_capability=(9, 0),
                uuid="GPU-example",
                physical_index=2,
            )
        ],
    )
    facts = SimpleNamespace(
        installed_backend="cuda",
        runtime_version="synthetic",
        hardware=context,
        implemented_accounting_adapter="nvidia-smi",
        limitations=(),
    )
    # The unchanged exp pin intentionally predates this additive API.
    monkeypatch.setattr(hardware, "inspect_gpu_runtime", lambda: facts, raising=False)
    monkeypatch.setattr(
        accounting,
        "sample_device_baseline",
        lambda device: accounting.DeviceBaselineSnapshot(
            device=device,
            telemetry_available=True,
            sampled_at=0.0,
            device_total_mib=192 * 1024,
            device_used_mib=0,
            device_free_mib=192 * 1024,
            processes=(),
            process_count=0,
        ),
    )
    calls = []
    monkeypatch.setattr(
        hardware.torch,
        "zeros",
        lambda *a, **kw: (
            calls.append(("allocate", a, kw))
            or SimpleNamespace(add_=lambda value: calls.append(("kernel", value)))
        ),
    )
    monkeypatch.setattr(
        hardware.torch.cuda, "synchronize", lambda index: calls.append(("sync", index))
    )
    monkeypatch.setattr(
        hardware.torch.cuda,
        "get_device_properties",
        lambda *_: pytest.fail("duplicate discovery"),
    )
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **kw: pytest.fail("duplicate driver query")
    )
    return facts, calls


def request(**changes):
    return gpu_check.GpuCheckRequest(
        trial_vram_gib=96.0, formal_vram_gib=128.0, **changes
    )


def test_arbitrary_large_device_and_remapped_physical_index_use_logical_zero(native):
    facts, calls = native
    report = gpu_check.check_gpu(request())
    assert report.capacity_gib == 192
    assert report.device_uuid == "GPU-example"
    assert calls == [
        ("allocate", (1,), {"device": "cuda:0"}),
        ("kernel", 1),
        ("sync", 0),
    ]
    assert facts.hardware.devices[0].physical_index == 2


@pytest.mark.parametrize(
    "failure",
    ["name", "capacity", "rocm", "identity", "device", "visibility", "backend"],
)
def test_unusable_facts_refuse_before_any_kernel(native, failure):
    facts, calls = native
    selected = request()
    message = {
        "name": "Expected GPU",
        "capacity": "below physical capacity",
        "rocm": "accounting is not implemented",
        "identity": "identity is unavailable",
        "device": "No usable",
        "visibility": "one visible",
        "backend": "No usable",
    }[failure]
    if failure == "name":
        selected = request(expected_name="H100")
    elif failure == "capacity":
        facts.hardware = facts.hardware.model_copy(
            update={"total_memory_bytes": 128 * 1024**3}
        )
    elif failure == "rocm":
        facts.installed_backend, facts.implemented_accounting_adapter = "rocm", None
    elif failure == "identity":
        facts.hardware = facts.hardware.model_copy(
            update={"active_device_uuid": None, "devices": []}
        )
    elif failure == "device":
        facts.hardware = facts.hardware.model_copy(update={"device_available": False})
    elif failure == "visibility":
        facts.hardware = facts.hardware.model_copy(update={"visible_device_count": 2})
    else:
        facts.installed_backend = "none"
    with pytest.raises(ValueError, match=message):
        gpu_check.check_gpu(selected)
    assert calls == []


def test_explicit_saved_name_is_trimmed_and_preserved(native):
    assert (
        gpu_check.check_gpu(request(expected_name=" NVIDIA ")).device_name
        == "Arbitrary NVIDIA device"
    )


@pytest.mark.parametrize("failed_query", ["unavailable", "exception"])
def test_implemented_adapter_and_uuid_require_real_queries_before_kernel(
    native, monkeypatch, failed_query
):
    facts, calls = native
    assert facts.implemented_accounting_adapter == "nvidia-smi"
    assert facts.hardware.active_device_uuid == "GPU-example"

    def query(device):
        assert device.uuid == "GPU-example"
        if failed_query == "exception":
            raise OSError("private-driver-output")
        return accounting.DeviceBaselineSnapshot(
            device=device,
            telemetry_available=False,
            sampled_at=0.0,
        )

    monkeypatch.setattr(accounting, "sample_device_baseline", query)
    with pytest.raises(ValueError, match="queries") as error:
        gpu_check.check_gpu(request())
    assert "private-driver-output" not in str(error.value)
    assert calls == []


def test_missing_new_api_is_named_pair_failure_without_old_probe(monkeypatch):
    monkeypatch.delattr(hardware, "inspect_gpu_runtime", raising=False)
    monkeypatch.setattr(
        hardware, "discover", lambda: pytest.fail("old discovery fallback")
    )
    with pytest.raises(ValueError, match="qualified infra/exp revision pair"):
        gpu_check.check_gpu(request())


def test_kernel_failure_is_actionable_without_exception_payload(native, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("do-not-print-environment")

    monkeypatch.setattr(hardware.torch, "zeros", fail)
    with pytest.raises(ValueError, match="kernel witness failed") as error:
        gpu_check.check_gpu(request())
    assert "do-not-print-environment" not in str(error.value)


def test_discovery_failure_is_not_replaced_by_cached_manifest(native, monkeypatch):
    def fail():
        raise RuntimeError("private-driver-output")

    monkeypatch.setattr(hardware, "inspect_gpu_runtime", fail)
    monkeypatch.setattr(
        hardware, "get_or_create", lambda *a: pytest.fail("cached fallback")
    )
    with pytest.raises(ValueError, match="property discovery failed") as error:
        gpu_check.check_gpu(request())
    assert "private-driver-output" not in str(error.value)
    assert native[1] == []


def settings(tmp_path):
    infra = tmp_path / "infra"
    python = infra / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("test stub, never executed")
    python.chmod(0o700)
    return SimpleNamespace(
        infra_checkout=infra,
        workspace=tmp_path / "run",
        gpu=None,
        vram_gib=8.0,
        trial_vram_gib=12.0,
        formal_vram_gib=None,
    )


def test_adapter_uses_selected_interpreter_effective_budgets_and_no_overlay(
    tmp_path, monkeypatch
):
    selected = settings(tmp_path)
    monkeypatch.setenv("PYTHONPATH", "/foreign")

    def child(command, **kwargs):
        assert command == [
            str(selected.infra_checkout / ".venv/bin/python"),
            str(runtime.Path(runtime.__file__).with_name("gpu_check.py")),
        ]
        assert kwargs["cwd"] == selected.infra_checkout
        assert "PYTHONPATH" not in kwargs["env"]
        assert json.loads(kwargs["input"]) == {
            "expected_name": None,
            "trial_vram_gib": 12.0,
            "formal_vram_gib": 8.0,
        }
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=gpu_check.GpuCheckReport(
                installed_backend="cuda",
                runtime_version="synthetic",
                device_name="Any GPU",
                capacity_gib=24.0,
                device_uuid="GPU-example",
                limitations=(),
            ).model_dump_json(),
        )

    monkeypatch.setattr(subprocess, "run", child)
    assert "live admission/accounting checks still required" in runtime.verify_gpu(
        selected
    )


@pytest.mark.parametrize("outcome", ["bad-json", "child-error", "timeout", "refusal"])
def test_adapter_refuses_bad_child_results_without_dumping_output(
    tmp_path, monkeypatch, outcome
):
    selected = settings(tmp_path)

    def child(command, **kwargs):
        if outcome == "child-error":
            raise subprocess.CalledProcessError(1, command, stderr="private-output")
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(command, 60, stderr="private-output")
        output = (
            "private-output"
            if outcome == "bad-json"
            else gpu_check.GpuCheckFailure(
                message="required accounting unavailable"
            ).model_dump_json()
        )
        return subprocess.CompletedProcess(command, 0, stdout=output)

    monkeypatch.setattr(subprocess, "run", child)
    with pytest.raises(ValueError) as error:
        runtime.verify_gpu(selected)
    assert "private-output" not in str(error.value)


@pytest.mark.parametrize("model", [TutorialExperiment, PetExperiment])
def test_saved_large_budget_reaches_shared_check_and_bad_values_never_do(
    tmp_path, model
):
    values = {
        "infra_checkout": tmp_path / "infra",
        "data_dir": tmp_path / "data",
        "workspace": tmp_path / "run",
        "run_name": "demo",
        "composition": tmp_path / "task.yaml",
        "llm_config": tmp_path / "llm.json",
        "vram_gib": 96.0,
        "gpu": " NVIDIA ",
    }
    if model is PetExperiment:
        values["workflow"] = tmp_path / "workflow.json"
    else:
        values["version"] = "siderius-tess-tutorial-v1"
    saved = model.model_validate(values)
    assert saved.vram_gib == 96.0 and saved.gpu == "NVIDIA"
    assert (
        gpu_check.GpuCheckRequest(
            expected_name=saved.gpu,
            trial_vram_gib=saved.vram_gib,
            formal_vram_gib=saved.vram_gib,
        ).trial_vram_gib
        == 96.0
    )
    for value in (True, float("nan"), float("inf"), 0, -1):
        with pytest.raises(ValueError):
            model.model_validate({**values, "trial_vram_gib": value})


@pytest.mark.parametrize("task", ["tess", "tidmad", "project8", "ligo", "pet"])
def test_each_actual_preview_stays_off_the_gpu_path(tmp_path, monkeypatch, task):
    import importlib

    from core.planner_strategy_identity import PlannerStrategyIdentity

    package = {
        "tess": "tutorials.paper",
        "tidmad": "tutorials.paper.tidmad",
        "project8": "tutorials.paper.prepared",
        "ligo": "tutorials.paper.prepared",
        "pet": "tutorials.supplementary.pet",
    }[task]
    project_module = importlib.import_module(package + ".project")
    runner = importlib.import_module(package + ".runner")
    project, infra = tmp_path / "project", tmp_path / "infra"
    if task in ("project8", "ligo"):
        project_module.create_project(project, infra, task)
        model = runner.PreparedExperiment
    elif task == "pet":
        experiment_path = project_module.create_project(
            project, infra, tmp_path / "images"
        )
        model = PetExperiment
    else:
        project_module.create_project(project, infra)
        model = runner.TutorialExperiment if task == "tess" else runner.TidmadExperiment
    if task != "pet":
        experiment_path = project / "experiments" / f"{task}-experiment.json"
    selected = model.model_validate_json(experiment_path.read_text())
    if task in ("project8", "ligo"):
        selected.composition.parent.mkdir(parents=True)
        selected.composition.write_text("task_health: {none: true}\n")
        declaration = selected.composition.parent.parent / "declared/prepared.json"
        declaration.parent.mkdir()
        declaration.write_text(
            runner.PreparedDeclaration(
                task_id="phyts_project8_energy_dual"
                if task == "project8"
                else "phyts_ligo_chirp_mass",
                manifest_sha256="a" * 64,
                train_count=20,
                validation_count=10,
                channels=2,
                length=32,
                loss_indices=(0,),
            ).model_dump_json()
        )
    elif task == "pet":
        monkeypatch.setattr(runner, "inspect_data", lambda *a, **kw: {})
    assert selected.gpu is None
    monkeypatch.setattr(runner, "verify_framework_pin", lambda *a: "a" * 40)
    monkeypatch.setattr(runner, "verify_installed_framework", lambda *a: None)
    monkeypatch.setattr(
        runner,
        "verify_planner_setup",
        lambda *a, **kw: PlannerStrategyIdentity(
            name="test",
            version="1",
            content_sha256="b" * 64,
        ),
    )
    monkeypatch.setattr(runner, "composition_identity", lambda *a: "c" * 64)
    monkeypatch.setattr(
        runner, "credential_status", lambda *a: {"OPENAI_API_KEY": False}
    )
    monkeypatch.setattr(
        runner, "verify_gpu", lambda *a: pytest.fail("preview invoked GPU setup")
    )
    monkeypatch.setattr(
        gpu_check, "check_gpu", lambda *a: pytest.fail("preview invoked kernel adapter")
    )
    result = runner.inspect(selected, launch=False)
    report = result.model_dump() if task == "tess" else result
    assert report["gpu"] is None
