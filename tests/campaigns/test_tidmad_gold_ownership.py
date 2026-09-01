"""Ownership and scientific-treatment checks for the TIDMAD Gold campaign."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

import yaml


EXP_ROOT = Path(__file__).resolve().parents[2]
TASK = EXP_ROOT / "tasks" / "tidmad"
CAMPAIGN = EXP_ROOT / "campaigns" / "tidmad_gold"
STAGE1_HEALTH = CAMPAIGN / "workflows" / "stage1" / "health_checks.yaml"
LAUNCHER = CAMPAIGN / "scripts" / "run_gold_campaign.sh"
LLM_ROUTING = CAMPAIGN / "config" / "llm_routing.json"


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _campaign_env(generated_library: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(generated_library)
    return env


def test_gold_workflows_are_not_owned_by_the_static_task() -> None:
    """A task package must not carry campaign stage or authorization policy."""
    assert not (TASK / "workflows").exists()
    assert STAGE1_HEALTH.is_file()
    assert (CAMPAIGN / "workflows" / "stage2" / "README.md").is_file()


def test_stage1_keeps_amplitude_as_the_only_blocking_gate() -> None:
    """Catch reintroduction of the pre-calibration three-blocking-gate policy."""
    payload = yaml.safe_load(STAGE1_HEALTH.read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in payload["health_gates"]}

    assert gates["amplitude_collapse_blocking"]["gate_role"] == "blocking"
    assert gates["amplitude_collapse_blocking"]["on_fail"] == {
        "action": "invalidate_round"
    }
    assert gates["output_diversity_blocking"]["gate_role"] == "observational"
    assert gates["output_diversity_blocking"]["on_fail"] == {"action": "continue"}
    assert gates["output_std_blocking"]["gate_role"] == "observational"
    assert gates["output_std_blocking"]["on_fail"] == {"action": "continue"}


def test_stage2_has_no_executable_campaign_entrypoint() -> None:
    """Stage 2 must remain documentation-only until explicitly authorized."""
    stage2 = CAMPAIGN / "workflows" / "stage2"
    assert not any(stage2.glob("*.sh"))
    assert not any(stage2.glob("*.py"))


def test_stage1_dry_run_binds_external_campaign_to_selected_framework(
    tmp_path: Path,
) -> None:
    """Catch fallback to the old in-framework Gold paths or another checkout."""
    checkout = _siderius_checkout()
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    workspace.mkdir()
    generated.mkdir()
    fcnet_reference = tmp_path / "fcnet.json"
    fcnet_reference.write_text("{}\n", encoding="utf-8")

    completed = subprocess.run(
        [
            "bash",
            str(LAUNCHER),
            "--siderius-checkout",
            str(checkout),
            "--workspace_root",
            str(workspace),
            "--stage",
            "1",
            "--arm",
            "blindpod",
            "--fcnet_reference_json",
            str(fcnet_reference),
            "--stagger-seconds",
            "0",
            "--dry-run",
        ],
        cwd=EXP_ROOT,
        env=_campaign_env(generated),
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    command_lines = [
        line
        for line in completed.stdout.splitlines()
        if "sdsc_submission_scripts/run_chain.sh" in line
    ]
    commands = [shlex.split(line) for line in command_lines]
    assert len(commands) == 4
    command = commands[0]
    assert str(checkout / "sdsc_submission_scripts" / "run_chain.sh") in command
    assert command[command.index("--task_config") + 1] == str(
        CAMPAIGN / "task" / "task_config_regression.yaml"
    )
    assert command[command.index("--health_checks_config") + 1] == str(STAGE1_HEALTH)
    llm_configs = {
        candidate[candidate.index("--llm_config") + 1] for candidate in commands
    }
    assert llm_configs == {str(LLM_ROUTING)}
    assert not str(LLM_ROUTING).startswith(str(checkout))
    assert command[command.index("--min_formal_batch_size") + 1] == "1"
    assert command[command.index("--formal_time_budget_minutes") + 1] == "180"
    rules = json.loads(command[command.index("--workflow_parameter_rules") + 1])
    assert rules == {"model_config.segmentation_size": {"exact": 40_000}}
    assert "--required_segmentation_size" not in command


def test_gold_llm_routing_preserves_the_frozen_campaign_identity() -> None:
    """Catch campaign routing drift during transfer out of SIDERIUS."""
    routing = json.loads(LLM_ROUTING.read_text(encoding="utf-8"))

    assert routing == {
        "interpret": {"provider": "openai", "model_id": "gpt-5.5-2026-04-23"},
        "propose": {
            role: {"provider": "openai", "model_id": "gpt-5.5-2026-04-23"}
            for role in ("comparison", "reasoning", "proposing")
        },
        "implement": {"provider": "openai", "model_id": "gpt-5.5-2026-04-23"},
        "validate": {"provider": "openai", "model_id": "gpt-5.5-2026-04-23"},
        "tune": {
            role: {"provider": "openai", "model_id": "gpt-5.5-2026-04-23"}
            for role in ("planner", "reflector")
        },
        "lit_review": {
            role: {"provider": "deepseek", "model_id": "deepseek-v4-pro"}
            for role in ("main", "search")
        },
    }


def test_stage2_remains_refused_at_the_campaign_entrypoint(tmp_path: Path) -> None:
    """Stage 2 must not become reachable while launcher paths are separated."""
    checkout = _siderius_checkout()
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    registry = tmp_path / "registry"
    workspace.mkdir()
    generated.mkdir()
    registry.mkdir()

    completed = subprocess.run(
        [
            "bash",
            str(LAUNCHER),
            "--siderius-checkout",
            str(checkout),
            "--workspace_root",
            str(workspace),
            "--stage",
            "2",
            "--arm",
            "blindpod",
            "--design_registry",
            str(registry),
            "--dry-run",
        ],
        cwd=EXP_ROOT,
        env=_campaign_env(generated),
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert completed.returncode == 1
    assert "Stage 2 is NOT AUTHORIZED" in completed.stderr
    assert "STAGE 2 HAS NOT STARTED" in completed.stderr


def test_campaign_refuses_a_task_config_different_from_its_frozen_source(
    tmp_path: Path,
) -> None:
    """The launcher must validate the file it actually passes to the chain."""
    checkout = _siderius_checkout()
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    workspace.mkdir()
    generated.mkdir()
    changed_config = tmp_path / "changed_task.yaml"
    changed_config.write_text("task_description: changed\n", encoding="utf-8")

    completed = subprocess.run(
        [
            "bash",
            str(LAUNCHER),
            "--siderius-checkout",
            str(checkout),
            "--workspace_root",
            str(workspace),
            "--stage",
            "1",
            "--arm",
            "blindpod",
            "--task_config",
            str(changed_config),
            "--dry-run",
        ],
        cwd=EXP_ROOT,
        env=_campaign_env(generated),
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert completed.returncode == 1
    assert "differs from the frozen Gold task config" in completed.stderr
    assert str(changed_config) in completed.stderr
