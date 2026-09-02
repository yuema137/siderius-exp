"""Nebius single-band launch and staging-contract regression witnesses."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

EXP_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = EXP_ROOT / "campaigns" / "tidmad_gold" / "scripts" / "campaign_preflight.sh"


def _call(shell_body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{PREFLIGHT}"\n{shell_body}'],
        cwd=EXP_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )


def _stage_band(data_dir: Path, indices: range) -> None:
    for index in indices:
        for split in ("training", "validation"):
            (data_dir / f"abra_{split}_{index:04d}.h5").touch()


def test_single_band_staging_does_not_require_the_other_32_files(tmp_path: Path) -> None:
    """A correctly staged 0-3 host must not be rejected for absent other bands."""
    _stage_band(tmp_path, range(4))
    (tmp_path / "segment_anchors.json").write_text("{}\n", encoding="utf-8")
    result = _call(f'preflight_missing_data_inputs "{tmp_path}" true 0-3')
    assert result.returncode == 0, result.stdout + result.stderr


def test_selected_band_still_requires_both_splits_and_anchor(tmp_path: Path) -> None:
    """Existence-only staging may not omit a validation file or scoring ruler."""
    _stage_band(tmp_path, range(4, 10))
    (tmp_path / "abra_validation_0007.h5").unlink()
    result = _call(f'preflight_missing_data_inputs "{tmp_path}" true 4-9')
    assert result.returncode != 0
    assert "abra_validation_0007.h5" in result.stdout
    assert "segment_anchors.json" in result.stdout


def test_gold_workspace_check_uses_the_real_campaign_identity() -> None:
    """R8 must inspect the v015 directory that Stage 1 actually writes."""
    result = _call("preflight_band_workspace /persist goldpod 15-19")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "/persist/goldpod_v015_band15-19"


def test_blind_workspace_uses_the_same_campaign_identity_rule() -> None:
    """BlindPod resume/cold-start checks must not inspect a surrogate path."""
    result = _call("preflight_band_workspace /persist blindpod 4-9")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "/persist/blindpod_v015_band4-9"


def test_checksum_validation_is_scoped_to_the_selected_band(tmp_path: Path) -> None:
    """A single-band host verifies its eight bytes, not unstaged other bands."""
    _stage_band(tmp_path, range(4))
    manifest = tmp_path / "manifest.sha256"
    rows = []
    for path in sorted(tmp_path.glob("abra_*.h5")):
        rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")

    result = _call(
        f'preflight_data_checksum_errors "{tmp_path}" "{manifest}" 0-3'
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""

    (tmp_path / "abra_training_0002.h5").write_bytes(b"corrupt")
    corrupted = _call(
        f'preflight_data_checksum_errors "{tmp_path}" "{manifest}" 0-3'
    )
    assert "checksum mismatch for abra_training_0002.h5" in corrupted.stdout


def test_free_space_threshold_is_caller_owned_and_launch_blocking(
    tmp_path: Path,
) -> None:
    """A deployment threshold must fail closed without hardcoding one campaign size."""
    available = _call(f'preflight_free_space_check "{tmp_path}" 0')
    assert available.returncode == 0, available.stdout + available.stderr
    assert "required=0 GiB" in available.stdout

    impossible = _call(
        f'preflight_free_space_check "{tmp_path}" 999999999999'
    )
    assert impossible.returncode != 0
    assert "required=999999999999 GiB" in impossible.stdout


def test_gold_capacity_default_is_three_tib() -> None:
    """Omitting the deployment flag must retain a launch-blocking threshold."""
    result = _call('printf "%s\\n" "$GOLD_MINIMUM_FREE_GIB_DEFAULT"')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3072"


def test_terminal_eval_policy_refuses_single_workspace_provenance() -> None:
    """Gold must not silently wire four Strict Best units into one provenance root."""
    result = _call('printf "%s\\n" "$GOLD_TERMINAL_EVAL_POLICY"')
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "out_of_scope_multi_workspace_provenance"


def test_resume_requires_attributable_noncorrupt_state(tmp_path: Path) -> None:
    """Resume must reject wrong-arm state even when the inspector reports clean."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "run_invariants_lock.json").write_text(
        '{"experiment_arm": "blindpod"}\n', encoding="utf-8"
    )
    inspector = tmp_path / "inspector.py"
    inspector.write_text(
        "import sys\nprint('2' if '--next-iter' in sys.argv else 'CORRUPT=0 TAMPERED=0')\n",
        encoding="utf-8",
    )

    refused = _call(
        f'preflight_resume_workspace "{Path(sys.executable)}" "{inspector}" '
        f'"{workspace}" goldpod'
    )
    assert refused.returncode != 0
    assert "does not carry arm goldpod" in refused.stdout

    (workspace / "run_invariants_lock.json").write_text(
        '{"experiment_arm": "goldpod"}\n', encoding="utf-8"
    )
    accepted = _call(
        f'preflight_resume_workspace "{Path(sys.executable)}" "{inspector}" '
        f'"{workspace}" goldpod'
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    assert accepted.stdout.strip() == "2"


def test_preflight_main_reaches_the_summary_without_llm_or_gpu(tmp_path: Path) -> None:
    """A missing runtime asset must not abort the preflight between named rows."""
    siderius_checkout = os.environ.get("SIDERIUS_CHECKOUT")
    if not siderius_checkout:
        pytest.skip("SIDERIUS_CHECKOUT must name the exact framework checkout")
    framework_root = Path(siderius_checkout).resolve()
    framework_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=framework_root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    exp_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=EXP_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    workspace = tmp_path / "workspace"
    data_dir = tmp_path / "data"
    generated = tmp_path / "generated"
    workspace.mkdir()
    data_dir.mkdir()
    generated.mkdir()
    completed = subprocess.run(
        [
            "bash",
            str(PREFLIGHT),
            "--workspace-root",
            str(workspace),
            "--arm",
            "blindpod",
            "--revision",
            exp_revision,
            "--siderius-checkout",
            str(framework_root),
            "--siderius-revision",
            framework_revision,
            "--data_dir",
            str(data_dir),
            "--only",
            "0-3",
            "--minimum-free-gib",
            "0",
            "--skip-llm-smoke",
            "--",
            "--healthgate_mode",
            "blocking",
            "--result_authority",
            "scientific",
        ],
        cwd=EXP_ROOT,
        env={
            **os.environ,
            "SIDERIUS_CHECKOUT": str(framework_root),
            "SIDERIUS_GENERATED_LIBRARY_DIR": str(generated),
        },
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    output = completed.stdout + completed.stderr
    assert "CAMPAIGN PREFLIGHT SUMMARY" in output, output
    assert "R2b pinned import resolution" in output
    assert "R9 LLM smoke SKIPPED" in output
    assert "R10 terminal evaluation OUT OF SCOPE" in output
