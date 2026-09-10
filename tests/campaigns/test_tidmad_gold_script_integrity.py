"""Campaign-owned integrity checks for the TIDMAD Gold shell entrypoints."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


EXP_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = EXP_ROOT / "campaigns" / "tidmad_gold"
SCRIPTS = CAMPAIGN / "scripts"
LIBRARY = SCRIPTS / "_gold_campaign_lib.sh"
EXECUTABLE_SCRIPTS = (
    SCRIPTS / "run_gold_campaign.sh",
    SCRIPTS / "stage1_search.sh",
    SCRIPTS / "stage1_run_band.sh",
    SCRIPTS / "stage2_strict_retrain.sh",
    SCRIPTS / "campaign_preflight.sh",
)
SHELL_SCRIPTS = (*EXECUTABLE_SCRIPTS, LIBRARY)


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _bash(
    *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", *args],
        cwd=EXP_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


@pytest.mark.parametrize("script", SHELL_SCRIPTS, ids=lambda path: path.name)
def test_campaign_shell_scripts_parse(script: Path) -> None:
    """A transferred campaign script must remain valid Bash source."""
    completed = _bash("-n", str(script))

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("script", EXECUTABLE_SCRIPTS, ids=lambda path: path.name)
def test_campaign_entrypoints_use_the_source_safe_guard(script: Path) -> None:
    """Sourcing an entrypoint must not dispatch its workload."""
    source = script.read_text(encoding="utf-8")

    assert '[[ "${BASH_SOURCE[0]}" == "$0" ]]' in source


@pytest.mark.parametrize("script", EXECUTABLE_SCRIPTS, ids=lambda path: path.name)
def test_sourcing_a_campaign_entrypoint_only_defines_it(script: Path) -> None:
    """Prevent recurrence of the 2026-07-31 source-time launcher incident."""
    completed = _bash("-c", f"source '{script}'; printf '%s\\n' SOURCED_OK")

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines()[-1] == "SOURCED_OK"


def test_campaign_library_refuses_direct_execution() -> None:
    """The shared library must not masquerade as a campaign entrypoint."""
    completed = _bash(str(LIBRARY))

    assert completed.returncode != 0
    assert "source it" in completed.stderr


def test_campaign_launch_refuses_an_implicit_data_root(tmp_path: Path) -> None:
    """A launch cannot pass preflight and later depend on ambient task data."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    completed = _bash(
        str(SCRIPTS / "run_gold_campaign.sh"),
        "--siderius-checkout",
        str(_siderius_checkout()),
        "--workspace_root",
        str(workspace),
        "--stage",
        "1",
        "--arm",
        "blindpod",
        "--dry-run",
    )

    assert completed.returncode != 0
    assert (
        "--data_dir must name an existing caller-owned dataset directory"
        in completed.stderr
    )


def test_missing_frozen_row_refuses_the_real_external_dry_run(tmp_path: Path) -> None:
    """Deleting one required row must fail by name before band dispatch."""
    isolated_campaign = tmp_path / "campaign"
    shutil.copytree(CAMPAIGN, isolated_campaign)
    isolated_library = isolated_campaign / "scripts" / LIBRARY.name
    original = isolated_library.read_text(encoding="utf-8")
    mutated = original.replace('    "trial_time_budget_minutes=30"\n', "")
    assert mutated != original, "mutation did not match the frozen row"
    isolated_library.write_text(mutated, encoding="utf-8")

    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    workspace.mkdir()
    generated.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    fcnet_reference = tmp_path / "fcnet.json"
    fcnet_reference.write_text("{}\n", encoding="utf-8")
    env = os.environ.copy()
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(generated)

    completed = _bash(
        str(isolated_campaign / "scripts" / "run_gold_campaign.sh"),
        "--siderius-checkout",
        str(_siderius_checkout()),
        "--workspace_root",
        str(workspace),
        "--data_dir",
        str(data_dir),
        "--stage",
        "1",
        "--arm",
        "blindpod",
        "--fcnet_reference_json",
        str(fcnet_reference),
        "--stagger-seconds",
        "0",
        "--dry-run",
        env=env,
    )

    assert completed.returncode != 0
    assert "trial_time_budget_minutes" in completed.stderr
    assert "FROZEN TABLE MISSING VALUE" in completed.stderr


def _campaign_budget_values(env: dict[str, str]) -> tuple[str, str]:
    completed = _bash(
        "-c",
        f"source '{LIBRARY}'; "
        "gold_frozen_value formal_time_budget_minutes; "
        "printf '%s\\n' \"$GOLD_BYPASS_FORMAL_TIME_BUDGET_MINUTES\"",
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    formal, bypass = completed.stdout.splitlines()
    return formal, bypass


def test_campaign_budget_defaults_are_owned_here() -> None:
    """Catch fallback to the retired in-framework 120/200 policy."""
    env = os.environ.copy()
    env.pop("GOLD_FORMAL_TIME_BUDGET_MINUTES", None)
    env.pop("GOLD_BYPASS_FORMAL_TIME_BUDGET_MINUTES", None)

    assert _campaign_budget_values(env) == ("180", "240")


def test_explicit_campaign_budget_overrides_reach_the_library() -> None:
    """Catch a bare assignment that silently discards an operator binding."""
    env = os.environ.copy()
    env["GOLD_FORMAL_TIME_BUDGET_MINUTES"] = "181"
    env["GOLD_BYPASS_FORMAL_TIME_BUDGET_MINUTES"] = "241"

    assert _campaign_budget_values(env) == ("181", "241")
