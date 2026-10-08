"""Catch lost tutorial strategy bindings and cross-environment provider drift."""

import json
import subprocess
from pathlib import Path

import pytest
from agent.planner_strategy import resolve_planner_strategy
from workflows.llm_config import WorkflowLLMConfig

from tutorials.shared import planner_setup
from tutorials.shared.llm_setup import TEST_LLM_CONFIG, write_test_llm_config


@pytest.mark.parametrize("task", ["tess", "tidmad", "project8", "ligo", "pet"])
def test_initialized_projects_use_independent_test_routing(tmp_path, task):
    """Every initializer uses native Luna routing and refuses existing projects."""
    if task == "tess":
        from tutorials.paper.project import create_project
    elif task == "tidmad":
        from tutorials.paper.tidmad.project import create_project
    elif task == "pet":
        from tutorials.supplementary.pet.project import create_project as pet

        def create_project(project, infra):
            pet(project, infra, tmp_path / "images")
    else:
        from tutorials.paper.prepared.project import create_project as prepared

        def create_project(project, infra):
            prepared(project, infra, task)

    project = tmp_path / "user project"
    create_project(project, tmp_path / "infra")
    saved = project / "llm/agents.json"
    assert saved.read_bytes() == TEST_LLM_CONFIG.read_bytes()
    data = json.loads(saved.read_text())
    assert data["tune"]["planner_strategy"] == "native-timing-v1"
    saved.write_text('{"user-owned": true}\n')
    with pytest.raises(ValueError, match="(new|existing|fresh)"):
        create_project(project, tmp_path / "infra")
    assert saved.read_text() == '{"user-owned": true}\n'


def test_test_config_writer_never_overwrites(tmp_path):
    destination = tmp_path / "agents.json"
    write_test_llm_config(destination)
    destination.write_text('{"user-owned": true}\n')
    with pytest.raises(FileExistsError):
        write_test_llm_config(destination)
    assert destination.read_text() == '{"user-owned": true}\n'


@pytest.mark.parametrize(
    "role, prefix",
    [(name, "") for name in ("interpret", "data_analysis", "implement", "validate")]
    + [("propose", stage + "_") for stage in ("comparison", "reasoning", "proposing")]
    + [("tune", ""), ("tune", "reflect_")]
    + [("lit_review", "llm_"), ("lit_review", "search_llm_")],
)
def test_all_eleven_resolved_routes_select_luna(role, prefix):
    routing = WorkflowLLMConfig.from_json(str(TEST_LLM_CONFIG))
    projected = routing.get(role)
    assert projected[prefix + "provider"] == "openai"
    assert projected[prefix + "model_id"] == "gpt-6-luna"
    assert projected[prefix + "reasoning_effort"] == "medium"
    assert routing.tune.planner_strategy == "native-timing-v1"


def test_profile_does_not_claim_unsupported_literature_retry_controls():
    data = json.loads(TEST_LLM_CONFIG.read_text())
    assert "max_retries" not in data["lit_review"]["main"]
    assert "max_retries" not in data["lit_review"]["search"]
    routing = WorkflowLLMConfig.model_validate(data)
    for role in (
        "interpret",
        "data_analysis",
        "implement",
        "validate",
        "propose",
        "tune",
    ):
        assert routing.get(role)["max_retries"] == 1


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
        assert "native-timing-v1 is built into infra" in message
        assert "uv pip install" not in message
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
