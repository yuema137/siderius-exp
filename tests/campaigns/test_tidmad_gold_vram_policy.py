"""Campaign-owned Stage-1 VRAM ceiling checks for TIDMAD Gold."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest


EXP_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = EXP_ROOT / "campaigns" / "tidmad_gold"
LAUNCHER = CAMPAIGN / "scripts" / "run_gold_campaign.sh"
TRIAL_VRAM_PROBE = "7.5"
FORMAL_VRAM_PROBE = "9.25"


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _base_args(workspace: Path, fcnet_reference: Path, data_dir: Path) -> list[str]:
    return [
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
    ]


def _run(
    tmp_path: Path,
    *extra: str,
    launcher: Path = LAUNCHER,
    dry_run: bool = True,
) -> subprocess.CompletedProcess[str]:
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    workspace.mkdir()
    generated.mkdir()
    fcnet_reference = tmp_path / "fcnet.json"
    fcnet_reference.write_text("{}\n", encoding="utf-8")
    env = os.environ.copy()
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(generated)
    command = [
        "bash",
        str(launcher),
        *_base_args(workspace, fcnet_reference, tmp_path),
    ]
    if dry_run:
        command.append("--dry-run")
    command.extend(extra)

    return subprocess.run(
        command,
        cwd=EXP_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def _supplied() -> tuple[str, ...]:
    return (
        "--gold_trial_vram_budget_gb",
        TRIAL_VRAM_PROBE,
        "--gold_formal_vram_budget_gb",
        FORMAL_VRAM_PROBE,
    )


def _band_commands(stdout: str) -> list[list[str]]:
    return [
        shlex.split(line)
        for line in stdout.splitlines()
        if "scripts/launch/run_chain.sh" in line
    ]


def _pairs(command: list[str]) -> dict[str, str]:
    return {
        command[index]: command[index + 1]
        for index in range(len(command) - 1)
        if command[index].startswith("--")
    }


def test_supplied_vram_ceilings_are_visible_and_reach_every_band(
    tmp_path: Path,
) -> None:
    """Distinct Trial/Formal values must agree across surface and child argv."""
    completed = _run(tmp_path, *_supplied())

    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = _band_commands(completed.stdout)
    assert len(commands) == 4
    for command in commands:
        pairs = _pairs(command)
        assert pairs["--trial_vram_budget_gb"] == TRIAL_VRAM_PROBE
        assert pairs["--formal_vram_budget_gb"] == FORMAL_VRAM_PROBE
        assert command.index("--no-cleanup_denoised") > command.index(
            "--formal_vram_budget_gb"
        )

    row = next(
        line
        for line in completed.stdout.splitlines()
        if "effective vram_budget=" in line
    )
    assert TRIAL_VRAM_PROBE in row
    assert FORMAL_VRAM_PROBE in row


def test_unsupplied_vram_ceiling_resolves_to_the_frozen_campaign_default(
    tmp_path: Path,
) -> None:
    """No override must resolve visibly and consistently to frozen 40/40."""
    completed = _run(tmp_path)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = _band_commands(completed.stdout)
    assert len(commands) == 4
    for command in commands:
        pairs = _pairs(command)
        assert pairs["--trial_vram_budget_gb"] == "40"
        assert pairs["--formal_vram_budget_gb"] == "40"
    assert (
        "effective vram_budget=trial:40 formal:40 source:campaign_default"
        in completed.stdout
    )


@pytest.mark.parametrize(
    ("extra", "expected"),
    [
        (("--gold_trial_vram_budget_gb", TRIAL_VRAM_PROBE), "INCOMPLETE"),
        (("--gold_formal_vram_budget_gb", FORMAL_VRAM_PROBE), "INCOMPLETE"),
        (
            (
                "--gold_trial_vram_budget_gb",
                "60GB",
                "--gold_formal_vram_budget_gb",
                FORMAL_VRAM_PROBE,
            ),
            "not a positive number",
        ),
        (
            (
                "--gold_trial_vram_budget_gb",
                TRIAL_VRAM_PROBE,
                "--gold_formal_vram_budget_gb",
                "abc",
            ),
            "not a positive number",
        ),
        (
            (
                "--gold_trial_vram_budget_gb",
                "0",
                "--gold_formal_vram_budget_gb",
                FORMAL_VRAM_PROBE,
            ),
            "not a positive number",
        ),
        (
            (
                "--gold_trial_vram_budget_gb",
                TRIAL_VRAM_PROBE,
                "--gold_formal_vram_budget_gb",
                "-8",
            ),
            "not a positive number",
        ),
    ],
)
def test_incomplete_or_malformed_vram_ceiling_refuses_before_dispatch(
    tmp_path: Path,
    extra: tuple[str, ...],
    expected: str,
) -> None:
    """Invalid paired ceilings must fail once at the campaign boundary."""
    completed = _run(tmp_path, *extra)

    assert completed.returncode != 0
    assert expected in completed.stderr
    assert "run_chain argv" not in completed.stdout


@pytest.mark.parametrize(
    "flag",
    ["--trial_vram_budget_gb", "--formal_vram_budget_gb"],
)
def test_chain_level_vram_override_is_refused(tmp_path: Path, flag: str) -> None:
    """A last-wins child spelling must not bypass the Gold declaration."""
    completed = _run(tmp_path, flag, "1")

    assert completed.returncode != 0
    assert flag in completed.stderr
    assert "GOLD_RESERVED_PASSTHROUGH" in completed.stderr


def test_chain_level_override_is_still_refused_after_gold_supply(
    tmp_path: Path,
) -> None:
    """Supplying approved ceilings must not disable the override guard."""
    completed = _run(tmp_path, *_supplied(), "--trial_vram_budget_gb", "1")

    assert completed.returncode != 0
    assert "GOLD_RESERVED_PASSTHROUGH" in completed.stderr


def _launch_manifest(tmp_path: Path, *extra: str) -> dict[str, object]:
    isolated_campaign = tmp_path / "campaign"
    shutil.copytree(
        CAMPAIGN, isolated_campaign, ignore=shutil.ignore_patterns("__pycache__")
    )
    stage1 = isolated_campaign / "scripts" / "stage1_search.sh"
    stage1.write_text(
        "#!/bin/bash\necho '[stub] dispatched'\nexit 0\n", encoding="utf-8"
    )

    completed = _run(
        tmp_path,
        *extra,
        launcher=isolated_campaign / "scripts" / "run_gold_campaign.sh",
        dry_run=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    manifests = sorted((tmp_path / "workspace").glob("gold_campaign_launch_*.json"))
    assert len(manifests) == 1
    return json.loads(manifests[0].read_text(encoding="utf-8"))


def test_launch_manifest_records_supplied_and_unsupplied_vram_state(
    tmp_path: Path,
) -> None:
    """The durable record must preserve values or the explicit pending state."""
    supplied_root = tmp_path / "supplied"
    supplied_root.mkdir()
    supplied = _launch_manifest(supplied_root, *_supplied())
    assert supplied["trial_vram_budget_gb"] == TRIAL_VRAM_PROBE
    assert supplied["formal_vram_budget_gb"] == FORMAL_VRAM_PROBE
    assert "operator_supplied" in supplied["vram_budget_provenance"]

    unsupplied_root = tmp_path / "unsupplied"
    unsupplied_root.mkdir()
    unsupplied = _launch_manifest(unsupplied_root)
    assert unsupplied["trial_vram_budget_gb"] == "40"
    assert unsupplied["formal_vram_budget_gb"] == "40"
    assert "campaign_default" in unsupplied["vram_budget_provenance"]


def test_gold_scripts_bind_only_the_frozen_40_vram_default() -> None:
    """No second numeric campaign authority may appear beside frozen 40."""
    scripts = [
        CAMPAIGN / "scripts" / name
        for name in (
            "run_gold_campaign.sh",
            "stage1_search.sh",
            "stage1_run_band.sh",
            "stage2_strict_retrain.sh",
            "_gold_campaign_lib.sh",
        )
    ]
    offenders = []
    for script in scripts:
        for lineno, line in enumerate(
            script.read_text(encoding="utf-8").splitlines(), 1
        ):
            code = line.split("#", 1)[0]
            if "VRAM_BUDGET" not in code and "vram_budget" not in code:
                continue
            if re.search(r"VRAM_BUDGET_GB=[\"']?\d", code) or re.search(
                r"--(?:trial|formal)_vram_budget_gb[\"']?\s+[\"']?\d", code
            ):
                offenders.append(f"{script.name}:{lineno}: {line.strip()}")

    assert len(offenders) == 1, offenders
    assert offenders[0].endswith("GOLD_DEFAULT_VRAM_BUDGET_GB=40")
