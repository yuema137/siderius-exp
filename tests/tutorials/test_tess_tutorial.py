"""Regressions for tutorial wiring and pre-effect refusals, not schema defaults."""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tutorials.paper import prepare_tess, runner


def settings(tmp_path: Path, **changes: object) -> runner.TutorialExperiment:
    values = {
        "version": "siderius-tess-tutorial-v1",
        "infra_checkout": tmp_path / "infra",
        "data_dir": tmp_path / "data",
        "workspace": tmp_path / "workspace",
        "run_name": "demo_001",
        "gpu": "RTX 5090",
        "iterations": 2,
        "epochs": 3,
        "trial_minutes": 2,
        "formal_minutes": 5,
        "vram_gib": 8,
    }
    values.update(changes)
    return runner.TutorialExperiment.model_validate(values)


def test_actual_renderer_keeps_no_prior_and_overrides_only_demo_knobs(tmp_path):
    """Dropping a treatment flag or appending a duplicate override changes the run."""
    command = runner.build_command(settings(tmp_path))
    for flag, value in {
        "--num_iterations": "2",
        "--max_epochs": "3",
        "--trial_max_epochs": "3",
        "--formal_max_epochs": "3",
        "--max_rounds": "2",
        "--formal_portion": "1.0",
        "--formal_eval_portion": "1.0",
        "--formal_training_scope_source": "operator",
        "--result_authority": "diagnostic",
        "--healthgate_mode": "blocking",
    }.items():
        assert command.count(flag) == 1
        assert runner.command_value(command, flag) == value
    assert "--no-data_analysis_enabled" in command
    assert "--no-ml_lit_review_enabled" in command
    assert "--advice" not in command
    assert "--trial_portion" not in command
    assert "--no_auto_resume" in command
    assert "--dry-run" not in command


def test_symlink_alias_cannot_put_workspace_inside_source(tmp_path):
    """Lexical-only containment would accept an alias pointing into a checkout."""
    infra = tmp_path / "infra"
    infra.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(infra, target_is_directory=True)
    with pytest.raises(ValueError, match="outside both"):
        runner.build_command(settings(tmp_path, workspace=alias / "run"))
    with pytest.raises(ValueError, match="separate"):
        runner.build_command(settings(tmp_path, workspace=tmp_path / "data/run"))


def test_gpu_mismatch_and_overbudget_refuse_before_cuda_probe(tmp_path, monkeypatch):
    """An unsupported GPU or impossible budget must not reach a training command."""
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 0, stdout="NVIDIA GeForce RTX 5090, 32607\n"
        )

    monkeypatch.setattr(runner.subprocess, "run", run)
    with pytest.raises(ValueError, match="expected one H100"):
        runner.verify_gpu(settings(tmp_path, gpu="H100"))
    with pytest.raises(ValueError, match="physical capacity"):
        runner.verify_gpu(settings(tmp_path, vram_gib=40))
    assert len(calls) == 2 and all(command[0] == "nvidia-smi" for command in calls)


def test_environment_displaces_ambient_plugins_but_keeps_launch_key(
    tmp_path, monkeypatch
):
    """An inherited plugin/calibration directory must not contaminate a fresh demo."""
    for key in (
        "SIDERIUS_PLUGIN_DIRS",
        "AGENT_GENERATED_DIR",
        "SIDERIUS_LOSS_DIRS",
        "PYTHONPATH",
    ):
        monkeypatch.setenv(key, "/foreign")
    monkeypatch.setenv("SIDERIUS_CALIBRATION_DIR", "/foreign-calibration")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-secret")
    config = settings(tmp_path)
    env = runner.child_environment(config)
    assert "PYTHONPATH" not in env and "SIDERIUS_PLUGIN_DIRS" not in env
    assert "AGENT_GENERATED_DIR" not in env and "SIDERIUS_LOSS_DIRS" not in env
    assert env["SIDERIUS_CALIBRATION_DIR"] == str(tmp_path / "workspace/calibration")
    assert env["OPENAI_API_KEY"] == "test-only-secret"
    assert "test-only-secret" not in config.model_dump_json()


def test_data_check_rejects_extra_split_and_wrong_keys(tmp_path, monkeypatch):
    """A runnable NPZ may still expose test data or a different scientific population."""
    from tasks.phyts_tess.tools import stage_data

    monkeypatch.setattr(
        stage_data, "_manifest_keys", lambda: {"train": {"star:1"}, "val": {"star:2"}}
    )
    data = tmp_path / "data"
    data.mkdir()
    np.savez(data / "tess_rotation_train.npz", **{"star:1": np.ones(3)})
    np.savez(data / "tess_rotation_val.npz", **{"star:2": np.ones(3)})
    assert len(runner.verify_data(data)) == 2
    (data / "test.npz").touch()
    with pytest.raises(ValueError, match="only"):
        runner.verify_data(data)
    (data / "test.npz").unlink()
    np.savez(data / "tess_rotation_val.npz", **{"other-star:2": np.ones(3)})
    with pytest.raises(ValueError, match="identity manifest"):
        runner.verify_data(data)
    np.savez(data / "tess_rotation_val.npz", **{"star:2": np.array([np.nan])})
    with pytest.raises(ValueError, match="invalid flux"):
        runner.verify_data(data)


def test_download_hash_refusal_does_not_publish_bad_bytes(tmp_path, monkeypatch):
    """A successful HTTP response is not proof of the frozen data identity."""
    monkeypatch.setattr(
        prepare_tess.urllib.request,
        "urlopen",
        lambda *a, **k: io.BytesIO(b"substituted"),
    )
    destination = tmp_path / "train.parquet"
    with pytest.raises(ValueError, match="checksum"):
        prepare_tess.download_file(
            "https://example.invalid/train", destination, "0" * 64
        )
    assert not destination.exists()
    assert not destination.with_suffix(".parquet.partial").exists()


def test_preparation_requests_only_pinned_train_and_val(tmp_path, monkeypatch):
    """Replacing the source list with a glob would accidentally download test data."""
    requested = []

    def download(url, destination, sha256):
        requested.append(url)
        destination.write_bytes(b"fixture")

    stage_args = []
    monkeypatch.setattr(prepare_tess, "download_file", download)
    monkeypatch.setattr(prepare_tess, "stage", lambda args: stage_args.extend(args))
    prepare_tess.prepare(tmp_path / "raw", tmp_path / "data")
    assert {url.rsplit("/", 1)[1] for url in requested} == {
        "tess_regression_train.parquet",
        "tess_regression_val.parquet",
    }
    assert all("9f203f4c338645a1e4b2c9dc7d6f820269ca5114" in url for url in requested)
    assert stage_args == [
        "--source",
        str(tmp_path / "raw"),
        "--data_dir",
        str(tmp_path / "data"),
    ]


def test_composition_probe_uses_infra_python_and_isolated_plugin_environment(
    tmp_path, monkeypatch
):
    """Resolving in the notebook process imports unrelated user-default plugins."""
    observed = {}

    def run(command, **kwargs):
        observed.update(command=command, **kwargs)
        return subprocess.CompletedProcess(command, 0, stdout="0" * 64 + "\n")

    monkeypatch.setattr(runner.subprocess, "run", run)
    monkeypatch.setenv("SIDERIUS_PLUGIN_DIRS", "/foreign")
    config = settings(tmp_path)
    assert runner.composition_identity(config, "/external/task.yaml") == "0" * 64
    assert observed["command"][0] == str(tmp_path / "infra/.venv/bin/python")
    assert observed["command"][-1] == "/external/task.yaml"
    assert "SIDERIUS_PLUGIN_DIRS" not in observed["env"]
    assert observed["env"]["SIDERIUS_GENERATED_LIBRARY_DIR"] == str(
        tmp_path / "workspace/generated_library"
    )


def test_notebook_result_cell_reads_real_schema_and_keeps_failed_score_missing(
    tmp_path,
):
    """Default Run All cannot catch a renamed field in the opt-in result reader."""
    import json

    from agent.schemas.hyperparam_tuning import ExperimentRecord, HyperparamTuningOutput
    from execute_tools.evaluation_metric import MetricResult

    rows = [
        ExperimentRecord(
            exp_id="trial",
            status="error_training",
            model_type="example",
            timestamp="2026-01-01T00:00:00Z",
            params={},
            is_trial=True,
        ),
        ExperimentRecord(
            exp_id="formal",
            status="success",
            model_type="example",
            timestamp="2026-01-01T00:01:00Z",
            params={},
            is_trial=False,
            logical_round=2,
            denoising_score=0.25,
            metric_result=MetricResult(metric_id="r2", direction="higher", scalar=0.25),
            health_gate_results=[
                {
                    "gate_name": "dispersion",
                    "execution_status": "failed",
                    "check_passed": False,
                    "would_invalidate_under_production_policy": False,
                    "resolved_action": "continue",
                    "gate_role": "observational",
                }
            ],
            scientific_authority={
                "declared_result_authority": "diagnostic",
                "authoritative": False,
            },
        ),
    ]
    output = HyperparamTuningOutput(
        run_name="example",
        model_type="example",
        file_index=0,
        status="completed",
        completed_rounds=2,
        total_attempts=2,
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:01:00Z",
        all_records=rows,
    )
    record_path = tmp_path / "run_output_example.json"
    record_path.write_text(output.model_dump_json())
    notebook = json.loads(
        (runner.ROOT / "tutorials/paper/notebooks/01_tess_tutorial.ipynb").read_text()
    )
    cell = next(
        "".join(c["source"])
        for c in notebook["cells"]
        if c["cell_type"] == "code" and "SELECTED_RECORD = None" in "".join(c["source"])
    )
    tables = []
    exec(  # noqa: S102 -- execute the trusted committed notebook result cell
        compile(
            cell.replace("SELECTED_RECORD = None", "SELECTED_RECORD = record_path"),
            "result-cell",
            "exec",
        ),
        {"record_path": record_path, "Path": Path, "display": tables.append},
    )
    table = tables[0]
    assert np.isnan(table["round"][0]) and table["round"][1] == 2
    assert table["role"].tolist() == ["Unspecified", "Formal"]
    assert table["status"].tolist() == ["error_training", "success"]
    assert np.isnan(table["score"][0]) and table["score"][1] == 0.25
    assert table["health_checks"][1][0]["passed"] is False
    assert table["health_checks"][1][0]["role"] == "observational"
    assert table["authority"][1]["authoritative"] is False


def test_credential_check_uses_selected_routing_and_never_returns_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-value")
    assert runner.credential_status(runner.WORKFLOW.parent / "agents.json") == {
        "OPENAI_API_KEY": True
    }
    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    assert runner.credential_status(runner.WORKFLOW.parent / "agents.json") == {
        "OPENAI_API_KEY": False
    }
    monkeypatch.setattr(
        runner, "required_workflow_api_keys", lambda *a, **k: {"GEMINI_API_KEY"}
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert runner.credential_status(runner.WORKFLOW.parent / "agents.json") == {
        "GEMINI_API_KEY": False
    }
