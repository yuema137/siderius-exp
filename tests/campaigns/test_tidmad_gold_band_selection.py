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

GPU_MAP = {"0-3": "0", "4-9": "1", "10-14": "2", "15-19": "3"}


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
            "--data_dir",
            str(tmp_path),
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


def test_stage1_dry_run_uses_the_frozen_band_to_gpu_map(tmp_path: Path) -> None:
    """Each band must target its distinct physical Gold GPU."""
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    workspace.mkdir()
    generated.mkdir()
    fcnet_reference = tmp_path / "fcnet.json"
    fcnet_reference.write_text("{}\n", encoding="utf-8")
    env = os.environ.copy()
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(generated)
    env.pop("CUDA_VISIBLE_DEVICES", None)

    completed = subprocess.run(
        [
            "bash",
            str(LAUNCHER),
            "--siderius-checkout",
            str(_siderius_checkout()),
            "--workspace_root",
            str(workspace),
            "--data_dir",
            str(tmp_path),
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

    assert completed.returncode == 0, completed.stdout + completed.stderr
    observed: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if "sdsc_submission_scripts/run_chain.sh" not in line:
            continue
        command = shlex.split(line)
        band = command[command.index("--data_scope") + 1]
        observed[band] = command[0].removeprefix("CUDA_VISIBLE_DEVICES=")
    assert observed == GPU_MAP


def test_unknown_band_has_no_gpu_assignment() -> None:
    """An unknown band must fail rather than sharing a valid GPU silently."""
    completed = subprocess.run(
        [
            "bash",
            "-c",
            f'source "{LIBRARY}"; gold_band_gpu 2-7',
        ],
        cwd=EXP_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert completed.returncode != 0
    assert "unknown band '2-7'" in completed.stderr


def test_external_gold_band_files_match_the_historical_x9_authority() -> None:
    """Catch scoring-file drift against the experiment-owned historical X9 launcher."""
    x9 = (
        EXP_ROOT
        / "campaigns"
        / "tidmad_x9"
        / "scripts"
        / "launch_prior_baseline_experiment.sh"
    ).read_text(encoding="utf-8")

    for band, files in {
        "0-3": "0,1,2,3",
        "4-9": "4,5,6,7,8,9",
        "10-14": "10,11,12,13,14",
        "15-19": "15,16,17,18,19",
    }.items():
        completed = subprocess.run(
            ["bash", "-c", f'source "{LIBRARY}"; gold_band_files "{band}"'],
            cwd=EXP_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout.strip() == files
        assert f'BAND_HEALTH_FILES="{files}"' in x9
