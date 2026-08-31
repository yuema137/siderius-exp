"""Campaign-owned frozen Stage-1 treatment checks for TIDMAD Gold."""

from __future__ import annotations

import hashlib
import os
import shlex
import subprocess
from pathlib import Path


EXP_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = EXP_ROOT / "campaigns" / "tidmad_gold" / "scripts" / "run_gold_campaign.sh"
GOLD_PACKAGE = EXP_ROOT / "campaigns" / "tidmad_gold"

FROZEN_CHAIN_VALUES = {
    "--num_iterations": "20",
    "--trial_portion": "0.1",
    "--train_portion": "0.1",
    "--eval_portion": "0.01",
    "--formal_portion": "1.0",
    "--formal_train_portion": "0.1",
    "--formal_eval_portion": "0.1",
    "--trial_max_epochs": "1",
    "--formal_max_epochs": "1",
    "--trial_time_budget_minutes": "30",
    "--formal_time_budget_minutes": "180",
    "--min_formal_batch_size": "1",
    "--skip_formal_min_delta": "-2.0",
    "--bypass_formal_time_budget_min_delta": "0.5",
    "--max_rounds": "3",
    "--attempts_per_round": "3",
    "--attempts_per_formal_round": "5",
    "--max_fail_rounds": "3",
    "--max_proposal_attempts": "3",
    "--max_impl_attempts": "3",
}
EXPECTED_FILES = {
    "0-3": "0,1,2,3",
    "4-9": "4,5,6,7,8,9",
    "10-14": "10,11,12,13,14",
    "15-19": "15,16,17,18,19",
}


def test_operator_approved_campaign_artifacts_are_byte_pinned() -> None:
    """Catch loss or silent replacement of the two immutable launch inputs."""
    expected = {
        "gold_advice_v6_regression.json": (
            "e621e1a5aa7ee87eab6978cb125a6e1b4aa944669a4761cccac908175ad23eae"
        ),
        "fcnet_band_references.json": (
            "f15ed7a5995dc86678a991ac26b76212361038d58d2cea96205a216f74f6d5a5"
        ),
    }
    observed = {
        name: hashlib.sha256((GOLD_PACKAGE / name).read_bytes()).hexdigest()
        for name in expected
    }
    assert observed == expected


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _dry_run(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    workspace.mkdir()
    generated.mkdir()
    fcnet_reference = tmp_path / "fcnet.json"
    fcnet_reference.write_text("{}\n", encoding="utf-8")
    env = os.environ.copy()
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(generated)

    return subprocess.run(
        [
            "bash",
            str(LAUNCHER),
            "--siderius-checkout",
            str(_siderius_checkout()),
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
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def _band_commands(stdout: str) -> dict[str, list[str]]:
    commands = {}
    lines = stdout.splitlines()
    for index, line in enumerate(lines):
        if "[gold-band] band " in line and "run_chain argv:" in line:
            band = line.split(" band ")[1].split(" run_chain")[0].strip()
            commands[band] = shlex.split(lines[index + 1])
    return commands


def _pairs(command: list[str]) -> dict[str, str]:
    return {
        command[index]: command[index + 1]
        for index in range(len(command) - 1)
        if command[index].startswith("--")
    }


def test_all_four_bands_bind_the_current_frozen_chain_values(tmp_path: Path) -> None:
    """Every band must consume the same twenty typed campaign values."""
    completed = _dry_run(tmp_path)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = _band_commands(completed.stdout)
    assert set(commands) == set(EXPECTED_FILES)
    for band, command in commands.items():
        pairs = _pairs(command)
        for flag, expected in FROZEN_CHAIN_VALUES.items():
            assert pairs.get(flag) == expected, (band, flag, pairs.get(flag))
        assert pairs["--bypass_formal_time_budget_minutes"] == "240"
        assert "--enable_chain_incumbent_formal_gates" in command
        assert "--max_epochs" not in command


def test_all_four_bands_bind_current_scope_arm_and_literature_treatment(
    tmp_path: Path,
) -> None:
    """Band identity and the explicit blind-arm treatment must stay coherent."""
    completed = _dry_run(tmp_path)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = _band_commands(completed.stdout)
    assert set(commands) == set(EXPECTED_FILES)
    for band, command in commands.items():
        pairs = _pairs(command)
        assert pairs["--data_scope"] == band
        assert pairs["--health_gate_files"] == EXPECTED_FILES[band]
        assert pairs["--experiment_arm"] == "blindpod"
        assert pairs["--workspace"].endswith(f"blindpod_v015_band{band}")
        assert pairs["--run_name"] == f"blindpod_v015_band{band}"
        assert "--ml_lit_review_enabled" in command
        assert "--no-ml_lit_review_enabled" not in command
        assert "--advice" not in command
