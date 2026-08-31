"""Campaign-owned refusal checks for the TIDMAD Gold entrypoint."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


EXP_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = EXP_ROOT / "campaigns" / "tidmad_gold" / "scripts" / "run_gold_campaign.sh"


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _run(
    tmp_path: Path,
    *,
    arm: str,
    with_advice: bool,
    extra: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    workspace.mkdir()
    generated.mkdir()
    fcnet_reference = tmp_path / "fcnet.json"
    fcnet_reference.write_text("{}\n", encoding="utf-8")
    advice = tmp_path / "advice.json"
    advice.write_text('{"propose": "campaign treatment"}\n', encoding="utf-8")
    env = os.environ.copy()
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(generated)

    command = [
        "bash",
        str(LAUNCHER),
        "--siderius-checkout",
        str(_siderius_checkout()),
        "--workspace_root",
        str(workspace),
        "--stage",
        "1",
        "--arm",
        arm,
        "--fcnet_reference_json",
        str(fcnet_reference),
        "--dry-run",
    ]
    if with_advice:
        command.extend(("--gold_advice_file", str(advice)))
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


@pytest.mark.parametrize("arm", ["with-prior-art", "without-prior-art"])
def test_x9_arm_names_are_refused_by_the_gold_entrypoint(
    tmp_path: Path, arm: str
) -> None:
    """X9 treatment labels must not enter Gold run identity."""
    completed = _run(tmp_path, arm=arm, with_advice=True)
    assert completed.returncode != 0
    assert "R-ARM-STAMP-1" in completed.stderr


def test_gold_arm_requires_its_advice_artifact(tmp_path: Path) -> None:
    """The treated arm must not launch without its declared treatment."""
    completed = _run(tmp_path, arm="goldpod", with_advice=False)
    assert completed.returncode != 0
    assert "--gold_advice_file" in completed.stderr


def test_blind_arm_refuses_an_advice_artifact(tmp_path: Path) -> None:
    """The control arm must not accept the treated arm's artifact."""
    completed = _run(tmp_path, arm="blindpod", with_advice=True)
    assert completed.returncode != 0
    assert "WITHOUT_ADVICE" in completed.stderr


def test_caller_cannot_override_a_frozen_campaign_flag(tmp_path: Path) -> None:
    """Campaign-fixed training scope must not be reopened by passthrough."""
    completed = _run(
        tmp_path,
        arm="blindpod",
        with_advice=False,
        extra=("--trial_portion", "0.5"),
    )
    assert completed.returncode != 0
    assert "--trial_portion" in completed.stderr
