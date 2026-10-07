"""Campaign-owned refusal checks for the TIDMAD Gold entrypoint."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

EXP_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = EXP_ROOT / "campaigns" / "tidmad_gold"
LAUNCHER = CAMPAIGN / "scripts" / "run_gold_campaign.sh"


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
    launcher: Path = LAUNCHER,
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
        str(launcher),
        "--siderius-checkout",
        str(_siderius_checkout()),
        "--workspace_root",
        str(workspace),
        "--data_dir",
        str(tmp_path),
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


@pytest.mark.parametrize(
    "flag",
    [
        "--trial_portion",
        "--max_rounds",
        "--attempts_per_round",
        "--attempts_per_formal_round",
        "--max_fail_rounds",
        "--max_proposal_attempts",
        "--max_impl_attempts",
        "--enable_chain_incumbent_formal_gates",
    ],
)
def test_caller_cannot_override_a_frozen_campaign_flag(
    tmp_path: Path, flag: str
) -> None:
    """Campaign-fixed training scope must not be reopened by passthrough."""
    completed = _run(
        tmp_path,
        arm="blindpod",
        with_advice=False,
        extra=(flag, "0.5"),
    )
    assert completed.returncode != 0
    assert flag in completed.stderr


def test_caller_cannot_override_the_frozen_llm_routing(tmp_path: Path) -> None:
    """A passthrough config must not replace the campaign-owned routing."""
    completed = _run(
        tmp_path,
        arm="blindpod",
        with_advice=False,
        extra=("--llm_config", "/tmp/unapproved-routing.json"),
    )
    assert completed.returncode != 0
    assert "--llm_config" in completed.stderr


def test_missing_campaign_llm_routing_refuses_before_dispatch(tmp_path: Path) -> None:
    """A damaged campaign package must not fall through to framework defaults."""
    isolated_campaign = tmp_path / "campaign_without_llm_config"
    shutil.copytree(
        CAMPAIGN,
        isolated_campaign,
        ignore=shutil.ignore_patterns("config", "__pycache__"),
    )

    completed = _run(
        tmp_path,
        arm="blindpod",
        with_advice=False,
        launcher=isolated_campaign / "scripts" / "run_gold_campaign.sh",
    )

    assert completed.returncode != 0
    assert "--llm_config" in completed.stderr
    assert "F-LLM-WIRE-1" in completed.stderr
    assert "gemini-3.1-pro-preview" in completed.stderr
    assert "run_chain argv" not in completed.stdout


@pytest.mark.parametrize("arm", ["with-prior-art", "without-prior-art"])
def test_preflight_refuses_retired_x9_before_environment_checks(
    tmp_path: Path, arm: str
) -> None:
    """The retained Gold preflight must not expose the retired X9 route."""
    completed = subprocess.run(
        ["bash", str(CAMPAIGN / "scripts" / "campaign_preflight.sh"), "--arm", arm],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode != 0
    assert "X9 is retired and no longer maintained" in completed.stderr
    assert "[preflight]" not in completed.stdout


def test_preflight_help_preserves_supported_usage_after_retirement() -> None:
    """A break in the comment header must not truncate operator-facing help."""
    completed = subprocess.run(
        ["bash", str(CAMPAIGN / "scripts" / "campaign_preflight.sh"), "--help"],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0
    assert "--arm goldpod|blindpod" in completed.stdout
    assert "--workspace-root" in completed.stdout
    assert "--siderius-checkout" in completed.stdout
