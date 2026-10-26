"""Exported TESS assets use explicit current infra, never exp's historical install."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "examples/native_candidate/tess/profile.json"


@pytest.fixture
def project(tmp_path):
    selected = os.environ.get("SIDERIUS_CHECKOUT")
    if not selected:
        pytest.skip(
            "set SIDERIUS_CHECKOUT to the exact framework in the example profile"
        )
    framework = Path(selected).resolve()
    profile = json.loads(PROFILE.read_text())
    revision = subprocess.check_output(
        ["git", "-C", str(framework), "rev-parse", "HEAD"], text=True
    ).strip()
    assert revision == profile["framework_revision"], (
        "select the example's declared framework, not another local checkout"
    )
    python = framework / ".venv/bin/python"
    assert python.is_file(), "run this framework checkout's own frozen sync first"
    home = tmp_path / "external TESS project"
    shutil.copytree(
        ROOT / "tasks/phyts_tess",
        home / "tasks/phyts_tess",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        ROOT / "examples/native_candidate", home / "examples/native_candidate"
    )
    data = tmp_path / "data path fixture"
    data.mkdir()  # No data validity or real execution is claimed by composition/preparation.
    credentials = tmp_path / "provider.json"
    credentials.write_text("{}\n")
    credentials.chmod(0o600)
    return home, data, framework, python, credentials


def recipe(project, *args):
    home, _, _, python, _ = project
    return subprocess.run(
        [
            str(python),
            str(home / "examples/native_candidate/materialize.py"),
            *map(str, args),
        ],
        cwd=home.parent,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )


def inspect(project):
    home, data, framework, _, _ = project
    result = recipe(
        project,
        "inspect",
        "--project",
        home,
        "--data",
        data,
        "--framework",
        framework,
        "--profile",
        home / "examples/native_candidate/tess/profile.json",
        "--output",
        home / "inspections/task.json",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return home / "inspections/task.json"


def accept(project, inspection, *args):
    return recipe(
        project,
        "accept",
        "--inspection",
        inspection,
        "--credential-file",
        project[4],
        *args,
    )


def test_inspection_is_not_acceptance_and_missing_flag_cannot_publish(project):
    """Composition success must never silently accept a task or produce runnable source."""
    report = inspect(project)
    home = project[0]
    assert (home / "llm/agents.json").is_file()
    assert not (home / "workflow.py").exists()
    result = accept(project, report)
    assert result.returncode == 2 and "--accept-task" in result.stderr
    assert not (home / "workflow.py").exists()
    assert not (home / "console-token").exists()


def test_bad_port_and_private_file_refuse_before_publication_then_retry(project):
    """Bad configuration must leave a retryable inspection, and secret diagnostics stay private."""
    report = inspect(project)
    home, _, _, _, credentials = project
    result = accept(project, report, "--accept-task", "--port", "1")
    assert result.returncode == 2
    assert not report.with_suffix(".accept-scratch").exists()
    assert not (home / "workflow.py").exists()
    credentials.write_text('{"OPENAI_API_KEY": ["private-marker"]}')
    result = accept(project, report, "--accept-task")
    assert (
        result.returncode == 2 and "private-marker" not in result.stdout + result.stderr
    )
    assert not report.with_suffix(".accept-scratch").exists()
    credentials.write_text("{}")
    result = accept(project, report, "--accept-task")
    assert result.returncode == 0, result.stdout + result.stderr
    before = (home / "workflow.py").read_bytes()
    assert accept(project, report, "--accept-task").returncode == 2
    assert (home / "workflow.py").read_bytes() == before


def test_task_change_after_inspection_cannot_inherit_acceptance(project):
    """A checked report cannot bless changed scientific task text."""
    report = inspect(project)
    declaration = project[0] / "tasks/phyts_tess/declared/task_config.yaml"
    before = declaration.read_text()
    assert "single TESS light curve." in before
    declaration.write_text(
        before.replace("single TESS light curve.", "single measured TESS light curve.")
    )
    result = accept(project, report, "--accept-task")
    assert result.returncode == 2 and "task changed after inspection" in result.stderr
    assert not (project[0] / "workflow.py").exists()


def test_native_prepare_captures_same_source_without_candidate_or_training(project):
    """A rendered diagram alone is insufficient: real native preparation must consume this source."""
    report = inspect(project)
    result = accept(project, report, "--accept-task")
    assert result.returncode == 0, result.stdout + result.stderr
    home, _, framework, python, credentials = project
    config = json.loads((home / "console.json").read_text())
    facts = json.loads(report.read_text())["observation"]["result"]["task"]
    assert config["credential_file"] == str(credentials)
    assert (
        config["tasks"][0]["task_revision"]["semantic_fingerprint"]
        == facts["semantic_fingerprint"]
    )
    assert config["editor_projects"][0]["source_file"] == str(home / "workflow.py")
    result = subprocess.run(
        [
            str(python),
            "-m",
            "tools.candidate_prepare",
            "--reusable-request",
            str(home / "prepare-request.json"),
        ],
        cwd=framework,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "prepared"
    envelope = Path(receipt["envelope"])
    assert (envelope / "workflow.py.snapshot").read_bytes() == (
        home / "workflow.py"
    ).read_bytes()
    candidate = json.loads(Path(receipt["candidate_request_path"]).read_text())
    assert [
        node["capability"]
        for node in candidate["preview"]["document"]["definition"]["nodes"]
    ] == ["proposal", "implementation", "validation"]
    assert not (envelope / "workspace").exists()
    assert not (
        home / "state/operations"
    ).exists()  # Direct preparation never submits a candidate.


def test_code_edit_invalidates_original_preparation_request(project):
    """A GUI/code source edit must not run through the old captured source identity."""
    report = inspect(project)
    assert accept(project, report, "--accept-task").returncode == 0
    home, _, framework, python, _ = project
    source = home / "workflow.py"
    source.write_text(source.read_text() + "\n# deliberate code edit\n")
    request = json.loads((home / "prepare-request.json").read_text())
    result = subprocess.run(
        [
            str(python),
            "-m",
            "tools.candidate_prepare",
            "--reusable-request",
            str(home / "prepare-request.json"),
        ],
        cwd=framework,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    assert result.returncode != 0
    assert not (home / "runs" / request["run_id"] / "workspace").exists()
    assert not (home / "state/operations").exists()
