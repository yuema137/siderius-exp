"""Campaign-owned checks for TIDMAD Gold deliverable retention."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


EXP_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = EXP_ROOT / "campaigns" / "tidmad_gold" / "scripts" / "run_gold_campaign.sh"


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _stage1_dry_run(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
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
            *extra,
        ],
        cwd=EXP_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def test_every_gold_band_retains_its_deliverables(tmp_path: Path) -> None:
    """Gold must type retention on every resolved band command."""
    completed = _stage1_dry_run(tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = [
        shlex.split(line)
        for line in completed.stdout.splitlines()
        if "sdsc_submission_scripts/run_chain.sh" in line
    ]
    assert len(commands) == 4
    for command in commands:
        assert "--no-cleanup_denoised" in command
        assert "--cleanup_denoised" not in command


def test_cleanup_override_is_refused_at_the_campaign_boundary(
    tmp_path: Path,
) -> None:
    """A caller must not replace the frozen Gold retention policy."""
    completed = _stage1_dry_run(tmp_path, "--cleanup_denoised")
    assert completed.returncode != 0
    assert "--cleanup_denoised" in completed.stderr
    assert "R-RETENTION-1" in completed.stderr
