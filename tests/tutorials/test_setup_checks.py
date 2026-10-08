"""Incomplete installations fail with repair steps before launching native work."""

import subprocess

import pytest

from tutorials.paper.preflight import require_ready, shell_setup_guard
from tutorials.paper.project import create_project
from tutorials.paper.runner import TutorialExperiment


def test_setup_collects_missing_inputs_without_exposing_secrets(tmp_path, monkeypatch):
    project = tmp_path / "project"
    create_project(project, tmp_path / "infra")
    settings = TutorialExperiment.model_validate_json(
        (project / "experiments/tess-experiment.json").read_text()
    )
    monkeypatch.setattr(
        "tutorials.paper.runner.credential_status",
        lambda _: {"OPENAI_API_KEY": False, "GEMINI_API_KEY": True},
    )
    monkeypatch.setenv("GEMINI_API_KEY", "do-not-print-this-secret")
    with pytest.raises(ValueError) as error:
        require_ready(settings, task="tess")
    message = str(error.value)
    assert "OPENAI_API_KEY" in message
    assert "do-not-print-this-secret" not in message
    assert "tess_rotation_train.npz" in message and "tess_rotation_val.npz" in message
    assert "nvidia-smi" not in message and "uv sync" in message
    assert "Fix:" in message and "No API call or training was started" in message


def test_shell_guard_runs_without_python_and_reports_missing_environment(tmp_path):
    import shlex

    source = f"EXP_CHECKOUT={shlex.quote(str(tmp_path))}\nEXPERIMENT=/missing.json\n"
    result = subprocess.run(
        ["bash", "-c", source + shell_setup_guard() + "\necho UNREACHABLE"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "uv sync --group dev --group tutorial --frozen" in result.stderr
    assert "UNREACHABLE" not in result.stdout


@pytest.mark.parametrize("task", ["tess", "tidmad"])
def test_both_cli_launches_stop_at_setup_errors_before_native_inspection(
    tmp_path, monkeypatch, task
):
    import importlib

    module = importlib.import_module(
        "tutorials.paper." + ("tidmad." if task == "tidmad" else "") + "runner"
    )
    project_module = importlib.import_module(
        "tutorials.paper." + ("tidmad." if task == "tidmad" else "") + "project"
    )
    project = tmp_path / task
    project_module.create_project(project, tmp_path / "infra")
    monkeypatch.setattr(
        "sys.argv",
        [
            "runner",
            "--experiment",
            str(project / "experiments" / f"{task}-experiment.json"),
            "--launch",
        ],
    )
    monkeypatch.setattr(
        module,
        "inspect",
        lambda *a, **kw: pytest.fail("native inspection ran despite incomplete setup"),
    )
    with pytest.raises(ValueError, match="Tutorial environment is not ready"):
        module.main()
