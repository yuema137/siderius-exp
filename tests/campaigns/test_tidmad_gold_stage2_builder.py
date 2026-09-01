"""Read-only campaign-owned checks for the unauthorized Gold Stage-2 builder."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

import pytest


EXP_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = EXP_ROOT / "campaigns" / "tidmad_gold"
STAGE2 = CAMPAIGN / "scripts" / "stage2_strict_retrain.sh"
LLM_ROUTING = CAMPAIGN / "config" / "llm_routing.json"
EXPECTED_FILES = {
    "0-3": "0,1,2,3",
    "4-9": "4,5,6,7,8,9",
    "10-14": "10,11,12,13,14",
    "15-19": "15,16,17,18,19",
}


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


@pytest.fixture
def stage2_inputs(tmp_path: Path) -> dict[str, Path]:
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    registry = tmp_path / "designs"
    workspace.mkdir()
    generated.mkdir()
    registry.mkdir()
    for design in ("wavenetA", "punetB", "rnnC", "fnoD"):
        (registry / f"{design}.json").write_text("{}\n", encoding="utf-8")
    advice = tmp_path / "advice.json"
    advice.write_text('{"propose": "frozen treatment"}\n', encoding="utf-8")
    return {
        "workspace": workspace,
        "generated": generated,
        "registry": registry,
        "advice": advice,
        "data": tmp_path,
    }


def _dry(inputs: dict[str, Path], *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["SIDERIUS_CHECKOUT"] = str(_siderius_checkout())
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(inputs["generated"])
    return subprocess.run(
        [
            "bash",
            str(STAGE2),
            "--workspace_root",
            str(inputs["workspace"]),
            "--data_dir",
            str(inputs["data"]),
            "--arm",
            "goldpod",
            "--gold_advice_file",
            str(inputs["advice"]),
            "--design_registry",
            str(inputs["registry"]),
            "--gold_trial_vram_budget_gb",
            "40",
            "--gold_formal_vram_budget_gb",
            "40",
            "--dry-run",
            *extra,
        ],
        cwd=EXP_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def _unit_commands(stdout: str) -> dict[str, list[str]]:
    commands = {}
    lines = stdout.splitlines()
    for index, line in enumerate(lines):
        if "[gold-stage2] unit " in line and "run_chain argv:" in line:
            unit = line.split(" unit ")[1].split(" gpu=")[0]
            commands[unit] = shlex.split(lines[index + 1])
    return commands


def _pairs(command: list[str]) -> dict[str, str]:
    return {
        command[index]: command[index + 1]
        for index in range(len(command) - 1)
        if command[index].startswith("--")
    }


def test_stage2_dry_run_builds_four_waves_of_four_frozen_units(
    stage2_inputs: dict[str, Path],
) -> None:
    """Catch reopening search or changing the design-by-band product."""
    completed = _dry(stage2_inputs)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = _unit_commands(completed.stdout)
    assert len(commands) == 16
    for unit, command in commands.items():
        design, band = unit.rsplit("_", 1)
        pairs = _pairs(command)
        assert command.count("--data_dir") == 1, unit
        assert pairs["--data_dir"] == str(stage2_inputs["data"].resolve()), unit
        assert pairs["--validation_fixed_candidate_plan"] == str(
            stage2_inputs["registry"] / f"{design}.json"
        )
        assert pairs["--num_iterations"] == "1"
        assert pairs["--data_scope"] == band
        assert pairs["--health_gate_files"] == EXPECTED_FILES[band]
        # Stage 2 retrains the Stage-1-selected model, loss, and training
        # design. Search admission ceilings therefore do not apply here.
        assert "--trial_vram_budget_gb" not in command
        assert "--formal_vram_budget_gb" not in command
        assert pairs["--llm_config"] == str(LLM_ROUTING)
        assert pairs["--formal_portion"] == "1.0"
        assert pairs["--formal_train_portion"] == "0.1"
        assert pairs["--formal_eval_portion"] == "1.0"
        assert pairs["--trial_max_epochs"] == "1"
        assert pairs["--formal_max_epochs"] == "1"
        assert "--enable_chain_incumbent_formal_gates" in command
        assert "--no-cleanup_denoised" in command
        assert "--max_epochs" not in command


def test_stage2_dry_run_skips_only_a_completed_unit(
    stage2_inputs: dict[str, Path],
) -> None:
    """Catch resume logic that re-runs a unit with an atomic completion marker."""
    completed_unit = stage2_inputs["workspace"] / "stage2" / "punetB_4-9"
    completed_unit.mkdir(parents=True)
    (completed_unit / "COMPLETE.json").write_text("{}\n", encoding="utf-8")

    completed = _dry(stage2_inputs)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "unit punetB_4-9: SKIP (COMPLETE.json exists)" in completed.stdout
    assert len(_unit_commands(completed.stdout)) == 15


def test_stage2_registry_requires_exactly_four_designs(
    stage2_inputs: dict[str, Path],
) -> None:
    """Catch a registry that silently changes the frozen 16-unit design."""
    (stage2_inputs["registry"] / "fnoD.json").unlink()

    completed = _dry(stage2_inputs)

    assert completed.returncode != 0
    assert "exactly FOUR" in completed.stderr
    assert not _unit_commands(completed.stdout)


def test_stage2_runtime_profile_reaches_every_unit(
    stage2_inputs: dict[str, Path],
) -> None:
    """Catch the independent Stage-2 builder dropping qualification identity."""
    profile_path = "/persistent/qualification/runtime_profiles_h100.json"
    profile_key = "nvidia_h100_80gb_hbm3/single"
    profile_sha = "c" * 64

    completed = _dry(
        stage2_inputs,
        "--gold_required_runtime_profile_path",
        profile_path,
        "--gold_required_runtime_profile",
        profile_key,
        "--gold_required_runtime_profile_sha256",
        profile_sha,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = _unit_commands(completed.stdout)
    assert len(commands) == 16
    for unit, command in commands.items():
        pairs = _pairs(command)
        assert pairs["--required_runtime_profile_path"] == profile_path, unit
        assert pairs["--required_runtime_profile"] == profile_key, unit
        assert pairs["--required_runtime_profile_sha256"] == profile_sha, unit
