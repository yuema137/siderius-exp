"""Campaign-owned checks for TIDMAD Gold Stage-1 band selection."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

import pytest


EXP_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = EXP_ROOT / "campaigns" / "tidmad_gold"
SCRIPTS = CAMPAIGN / "scripts"
LIBRARY = SCRIPTS / "_gold_campaign_lib.sh"
LAUNCHER = SCRIPTS / "run_gold_campaign.sh"

SELECTIONS = [
    ("0-3", ["0-3"]),
    ("4-9", ["4-9"]),
    ("10-14", ["10-14"]),
    ("15-19", ["15-19"]),
    ("0-3,4-9", ["0-3", "4-9"]),
    ("10-14,0-3", ["0-3", "10-14"]),
    ("4-9,15-19", ["4-9", "15-19"]),
    ("0-3,4-9,10-14", ["0-3", "4-9", "10-14"]),
    ("0-3,4-9,10-14,15-19", ["0-3", "4-9", "10-14", "15-19"]),
    (" 0-3 , 10-14 ", ["0-3", "10-14"]),
]


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _select(selection: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            "-c",
            f"source \"{LIBRARY}\"; gold_select_bands '{selection}'",
        ],
        cwd=EXP_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )


@pytest.mark.parametrize(("selection", "expected"), SELECTIONS)
def test_selection_succeeds_in_canonical_order(
    selection: str, expected: list[str]
) -> None:
    """A valid subset must emit canonical order and return success."""
    completed = _select(selection)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.split() == expected


def test_empty_selection_means_all_bands() -> None:
    """An omitted filter must preserve the complete four-band campaign."""
    completed = _select("")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.split() == ["0-3", "4-9", "10-14", "15-19"]


@pytest.mark.parametrize(
    ("selection", "reason"),
    [
        ("0-3,0-3", "duplicate"),
        ("nope", "unknown"),
        ("0-3,nope", "unknown"),
        (",", "selected nothing"),
    ],
)
def test_invalid_selection_is_refused_by_name(selection: str, reason: str) -> None:
    """The valid-subset fix must not weaken malformed-filter refusals."""
    completed = _select(selection)
    assert completed.returncode != 0
    assert reason in completed.stderr


def test_entrypoint_only_filter_reaches_exactly_one_band(tmp_path: Path) -> None:
    """Prove the operator-facing flag reaches the Stage-1 fan-out."""
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    workspace.mkdir()
    generated.mkdir()
    fcnet_reference = tmp_path / "fcnet.json"
    fcnet_reference.write_text("{}\n", encoding="utf-8")
    env = os.environ.copy()
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(generated)

    completed = subprocess.run(
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
            "--only",
            "0-3",
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

    assert completed.returncode == 0, completed.stdout + completed.stderr
    command_lines = [
        line
        for line in completed.stdout.splitlines()
        if "sdsc_submission_scripts/run_chain.sh" in line
    ]
    assert len(command_lines) == 1
    command = shlex.split(command_lines[0])
    assert command[command.index("--data_scope") + 1] == "0-3"
