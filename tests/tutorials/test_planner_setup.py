"""Catch lost tutorial strategy bindings and cross-environment provider drift."""

import json
import subprocess
from pathlib import Path

import pytest
from agent.planner_strategy import resolve_planner_strategy

from tutorials.paper import planner_setup


@pytest.mark.parametrize("task", ["tess", "tidmad", "project8", "ligo"])
def test_initialized_projects_keep_previous_planner(tmp_path, task):
    """Fails if any initializer bypasses the shared configuration copy."""
    if task == "tess":
        from tutorials.paper.project import create_project
    elif task == "tidmad":
        from tutorials.paper.tidmad.project import create_project
    else:
        from tutorials.paper.prepared.project import create_project as prepared

        def create_project(project, infra):
            prepared(project, infra, task)

    project = tmp_path / "user project"
    create_project(project, tmp_path / "infra")
    data = json.loads((project / "llm/agents.json").read_text())
    assert data["tune"]["planner_strategy"] == "legacy-9b78d505cb11-v1"


def test_copy_preserves_explicit_strategy_and_never_overwrites(tmp_path):
    """Detects lossy schema reserialization or replacement of an explicit choice."""
    source = tmp_path / "source.json"
    content = {
        "tune": {
            "planner_strategy": "native-timing-v1",
            "planner": {"provider": "openai", "model": "example-model"},
        },
        "description": "Preserve experiment metadata too",
    }
    source.write_text(json.dumps(content))
    before = source.read_bytes()
    destination = tmp_path / "agents.json"
    planner_setup.copy_llm_config(source, destination)
    assert json.loads(destination.read_text()) == content
    assert source.read_bytes() == before
    with pytest.raises(FileExistsError):
        planner_setup.copy_llm_config(source, destination)


@pytest.mark.parametrize("mode", ["match", "missing", "different"])
def test_preflight_compares_actual_child_identity_without_echoing_errors(
    tmp_path, monkeypatch, mode
):
    """Removing comparison, checking only a name, or echoing child stderr fails."""
    config = tmp_path / "agents.json"
    config.write_text('{"tune": {"planner_strategy": "native-timing-v1"}}')
    identity = resolve_planner_strategy("native-timing-v1").identity
    child = identity.model_copy(update={"content_sha256": "0" * 64})
    infra = tmp_path / "infra with spaces"

    def run(args, **kwargs):
        assert args[0] == str(infra / ".venv/bin/python")
        assert args[-1] == str(config)
        assert kwargs["env"] == {"BOUND_ENV": "yes"}
        assert kwargs["cwd"] == infra
        if mode == "missing":
            raise subprocess.CalledProcessError(1, args, stderr="private-test-key")
        return subprocess.CompletedProcess(
            args,
            0,
            stdout=(child if mode == "different" else identity).model_dump_json(),
        )

    monkeypatch.setattr(planner_setup.subprocess, "run", run)
    if mode == "match":
        assert (
            planner_setup.verify_planner_setup(
                config, infra, environment={"BOUND_ENV": "yes"}
            )
            == identity
        )
    else:
        with pytest.raises(ValueError) as error:
            planner_setup.verify_planner_setup(
                config, infra, environment={"BOUND_ENV": "yes"}
            )
        message = str(error.value)
        assert "private-test-key" not in message
        assert "uv pip install --python" in message
        assert "tune.planner_strategy" in message


def test_missing_exp_provider_refuses_before_child(tmp_path, monkeypatch):
    config = tmp_path / "agents.json"
    config.write_text('{"tune": {"planner_strategy": "uninstalled-test-provider"}}')
    monkeypatch.setattr(
        planner_setup.subprocess,
        "run",
        lambda *a, **k: pytest.fail("must refuse before child resolution"),
    )
    with pytest.raises(ValueError, match="Exp cannot load the selected planner"):
        planner_setup.verify_planner_setup(config, Path("/unused"), environment={})
