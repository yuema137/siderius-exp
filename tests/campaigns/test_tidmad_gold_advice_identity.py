"""Campaign-owned checks for the TIDMAD Gold advice identity."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest


EXP_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = EXP_ROOT / "campaigns" / "tidmad_gold" / "scripts"
LIBRARY = SCRIPTS / "_gold_campaign_lib.sh"
LAUNCHER = SCRIPTS / "run_gold_campaign.sh"


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _library_call(body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{LIBRARY}" 2>/dev/null || true\n{body}\n'],
        cwd=EXP_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )


@pytest.fixture
def advice(tmp_path: Path) -> tuple[Path, str]:
    path = tmp_path / "gold_advice.json"
    path.write_text('{"propose": "campaign treatment"}\n', encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign_identity_accepts_the_same_bytes_and_refuses_an_edit(
    advice: tuple[Path, str],
) -> None:
    """A staggered band must compare its own read with the campaign's read."""
    path, campaign_sha = advice
    accepted = _library_call(f'gold_arm_args goldpod "{path}" "{campaign_sha}"')
    assert accepted.returncode == 0, accepted.stderr

    path.write_text('{"propose": "edited after campaign binding"}\n', encoding="utf-8")
    refused = _library_call(f'gold_arm_args goldpod "{path}" "{campaign_sha}"')
    assert refused.returncode != 0
    assert "NOT the one this campaign bound" in refused.stderr
    assert campaign_sha in refused.stderr
    assert hashlib.sha256(path.read_bytes()).hexdigest() in refused.stderr


def test_direct_and_control_arm_identity_rules(advice: tuple[Path, str]) -> None:
    """Direct Gold binds its observation; Blind carries no advice identity."""
    path, campaign_sha = advice
    direct = _library_call(
        f'gold_arm_args goldpod "{path}" && printf "%s " "${{GOLD_ARM_ARGS[@]}}"'
    )
    assert direct.returncode == 0, direct.stderr
    assert f"--advice_sha256 {campaign_sha}" in direct.stdout

    blind = _library_call(
        'gold_arm_args blindpod "" && printf "%s " "${GOLD_ARM_ARGS[@]}"'
    )
    assert blind.returncode == 0, blind.stderr
    assert "--advice" not in blind.stdout

    contradicted = _library_call(f'gold_arm_args blindpod "" "{campaign_sha}"')
    assert contradicted.returncode != 0
    assert "blindpod refuses an inherited advice identity" in contradicted.stderr


def test_advice_identity_cannot_be_redeclared_as_passthrough() -> None:
    """A later chain argument must not replace the campaign-owned identity."""
    completed = _library_call("gold_refuse_reserved_passthrough --advice_sha256")
    assert completed.returncode != 0
    assert "--advice_sha256" in completed.stderr


def test_edited_advice_is_refused_at_the_band_boundary(
    tmp_path: Path, advice: tuple[Path, str]
) -> None:
    """Prove the identity reaches the real Stage-1 band entrypoint."""
    path, campaign_sha = advice
    path.write_text('{"propose": "edited before band spawn"}\n', encoding="utf-8")
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    workspace.mkdir()
    generated.mkdir()
    env = os.environ.copy()
    env["SIDERIUS_CHECKOUT"] = str(_siderius_checkout())
    env["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(generated)
    env.pop("CUDA_VISIBLE_DEVICES", None)

    completed = subprocess.run(
        [
            "bash",
            str(SCRIPTS / "stage1_run_band.sh"),
            "--band",
            "15-19",
            "--workspace_root",
            str(workspace),
            "--arm",
            "goldpod",
            "--gold_advice_file",
            str(path),
            "--gold_advice_sha256",
            campaign_sha,
            "--dry-run",
        ],
        cwd=EXP_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert completed.returncode != 0
    assert "NOT the one this campaign bound" in completed.stderr
    assert campaign_sha in completed.stderr


def test_all_stage1_bands_inherit_one_campaign_identity(
    tmp_path: Path, advice: tuple[Path, str]
) -> None:
    """The campaign observes once and transports that digest to four bands."""
    path, campaign_sha = advice
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
            "--stage",
            "1",
            "--arm",
            "goldpod",
            "--gold_advice_file",
            str(path),
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
        timeout=180,
    )

    assert completed.returncode == 0, (
        completed.stdout[-3000:] + completed.stderr[-3000:]
    )
    bands = [
        line for line in completed.stdout.splitlines() if "run_chain argv:" in line
    ]
    assert len(bands) == 4
    inherited = re.findall(r"--advice_sha256 ([0-9a-f]{64})", completed.stdout)
    assert len(inherited) == 4
    assert set(inherited) == {campaign_sha}


def test_launch_manifest_records_the_bound_advice_identity(
    tmp_path: Path, advice: tuple[Path, str]
) -> None:
    """The campaign record must describe the identity passed to its stages."""
    path, campaign_sha = advice
    workspace = tmp_path / "workspace"
    generated = tmp_path / "generated"
    registry = tmp_path / "registry"
    workspace.mkdir()
    generated.mkdir()
    registry.mkdir()
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
            "2",
            "--arm",
            "goldpod",
            "--gold_advice_file",
            str(path),
            "--design_registry",
            str(registry),
        ],
        cwd=EXP_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert completed.returncode == 1
    assert "Stage 2 is NOT AUTHORIZED" in completed.stderr
    manifests = list(workspace.glob("gold_campaign_launch_*_stage2.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["advice_path"] == str(path.resolve())
    assert manifest["advice_sha256"] == campaign_sha
