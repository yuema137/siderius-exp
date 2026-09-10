"""Real launcher/capture transport, without data execution, GPU, or LLM calls."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

EXP_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = EXP_ROOT / "campaigns/tidmad_x9/scripts"


@pytest.fixture
def surface_env(tmp_path):
    environment = dict(os.environ)
    for name in ("PYTHONPATH", "VIRTUAL_ENV", "SIDERIUS_PYTHON"):
        environment.pop(name, None)
    environment["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(tmp_path / "library")
    environment["SIDERIUS_CALIBRATION_DIR"] = str(tmp_path / "calibration")
    environment["CUDA_VISIBLE_DEVICES"] = ""
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _call(command, tmp_path, environment):
    return subprocess.run(
        command,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )


def _capture_command(environment, output):
    framework = Path(environment["SIDERIUS_CHECKOUT"])
    return [
        str(framework / ".venv/bin/python"),
        str(SCRIPTS / "campaign_arm_surface.py"),
        "--arm",
        "with-prior-art",
        "--baseline-isolation",
        "false",
        "--project-dir",
        str(framework),
        "--out",
        str(output),
    ]


def test_real_launcher_to_preflight_capture(tmp_path, surface_env):
    (tmp_path / "workspaces").mkdir()
    launch = _call(
        [
            "bash",
            str(SCRIPTS / "launch_prior_baseline_experiment.sh"),
            "--arm",
            "with-prior-art",
            "--band",
            "0-3",
            "--workspace-root",
            str(tmp_path / "workspaces"),
            "--dry-run",
            "--data_dir",
            str(tmp_path),
            "--healthgate_mode",
            "blocking",
            "--result_authority",
            "scientific",
        ],
        tmp_path,
        surface_env,
    )
    assert launch.returncode == 0, launch.stdout[-4000:] + launch.stderr
    capture = tmp_path / "launch.out"
    capture.write_text(launch.stdout)
    output = tmp_path / "surface.json"
    result = _call(
        [
            "bash",
            "-c",
            'source "$1"; pf_resolve_python; pf_capture_surface with-prior-art false "$2" "$3"',
            "capture-test",
            str(SCRIPTS / "campaign_preflight.sh"),
            str(output),
            str(capture),
        ],
        tmp_path,
        surface_env,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr
    surface = json.loads(output.read_text())
    assert surface["provenance"]["project_dir"] == surface_env["SIDERIUS_CHECKOUT"]
    assert surface["prompt_bytes"]["task.task_description"]["neutral"]


@pytest.mark.parametrize("manifest", [None, "", "relative/task.yaml"])
def test_bad_resolved_task_refuses_without_artifact(tmp_path, surface_env, manifest):
    capture = tmp_path / "launch.out"
    capture.write_text(json.dumps({"task_composition": manifest}))
    output = tmp_path / "must-not-exist" / "surface.json"
    result = _call(
        _capture_command(surface_env, output) + ["--resolved-launch", str(capture)],
        tmp_path,
        surface_env,
    )
    assert result.returncode == 2
    assert "task_composition" in result.stderr
    assert not output.parent.exists()


def test_missing_task_source_is_not_a_default_task(tmp_path, surface_env):
    output = tmp_path / "surface.json"
    result = _call(_capture_command(surface_env, output), tmp_path, surface_env)
    assert result.returncode == 2
    assert "--task-composition" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("task", ["tidmad", "oxford_iiit_pet"])
def test_selected_task_description_reaches_real_rendering(tmp_path, surface_env, task):
    from workflows.task_composition import compose_run_task_bindings
    from workflows.task_config import get_task_description

    manifest = EXP_ROOT / "tasks" / task / "compositions/bounded_qualification.yaml"
    description = get_task_description(
        compose_run_task_bindings(str(manifest)).task_config_values()
    )
    output = tmp_path / "surface.json"
    result = _call(
        _capture_command(surface_env, output) + ["--task-composition", str(manifest)],
        tmp_path,
        surface_env,
    )
    assert result.returncode == 0, result.stderr
    surface = json.loads(output.read_text())
    expected = hashlib.sha256(description.encode()).hexdigest()
    for mode in ("arm", "neutral"):
        assert (
            surface["prompt_bytes"]["task.task_description"][mode]["sha256"] == expected
        )
