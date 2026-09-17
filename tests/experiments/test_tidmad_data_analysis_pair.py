"""Matched TIDMAD Data Analysis arms differ only at the workflow edge."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml
from agent.schemas.data_analysis.assets import LegacyPartitionScope
from workflows.data_analysis_composition import DataAnalysisWorkflowConfig

ROOT = Path(__file__).resolve().parents[2]
PAIR = ROOT / "experiments/tidmad/data_analysis_pair"


def _pair_checkout() -> str:
    """Qualify this frozen experiment against its own pin, not the repo-wide pin."""

    configured = os.environ.get("SIDERIUS_DA_PAIR_CHECKOUT") or os.environ.get(
        "SIDERIUS_CHECKOUT"
    )
    if not configured:
        pytest.fail(
            "SIDERIUS_DA_PAIR_CHECKOUT must name the frozen experiment checkout"
        )
    if not Path(configured).is_dir():
        pytest.fail(f"Data Analysis pair checkout does not exist: {configured}")
    expected = (PAIR / "SIDERIUS_REVISION").read_text(encoding="utf-8").strip()
    actual = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=configured,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    if actual != expected:
        pytest.fail(
            "Data Analysis pair requires its experiment-local infra pin; "
            "set SIDERIUS_DA_PAIR_CHECKOUT to that exact checkout"
        )
    return configured


def _manifest(arm: str) -> dict:
    return yaml.safe_load((PAIR / f"task_composition_{arm}.yaml").read_text(encoding="utf-8"))


def _dry_run(arm: str, *, checkout: str, workspace: Path) -> list[str]:
    result = subprocess.run(
        [
            "bash",
            str(PAIR / "launch_arm.sh"),
            "--arm",
            arm,
            "--siderius-checkout",
            checkout,
            "--workspace",
            str(workspace),
            "--data_dir",
            str(workspace.parent / "unavailable-real-data"),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.startswith("DRY RUN: bash ")
    assert "DRY-RUN COMPLETE — 2 iterations walked, no side effects" in result.stdout
    return shlex.split(result.stdout.splitlines()[0].removeprefix("DRY RUN: "))


def _without_arm_fields(argv: list[str]) -> list[str]:
    differing = {"--task_composition", "--workspace", "--experiment_arm"}
    normalized: list[str] = []
    position = 0
    while position < len(argv):
        if argv[position] in differing:
            position += 2
        else:
            normalized.append(argv[position])
            position += 1
    return normalized


def test_pair_uses_one_static_task_and_one_literature_first_launch_contract(tmp_path: Path) -> None:
    on = _manifest("on")
    off = _manifest("off")
    assert {key: value for key, value in on.items() if key != "data_analysis"} == {
        key: value for key, value in off.items() if key != "data_analysis"
    }
    assert on["data_analysis"] == {"enabled": True, "config": "analysis_on.yaml"}
    assert off["data_analysis"] == {"enabled": False}

    checkout = _pair_checkout()
    on_argv = _dry_run("on", checkout=checkout, workspace=tmp_path / "on")
    off_argv = _dry_run("off", checkout=checkout, workspace=tmp_path / "off")
    assert _without_arm_fields(on_argv) == _without_arm_fields(off_argv)
    assert on_argv[on_argv.index("--scientific_evidence_order") + 1] == "literature_then_analysis"
    assert "--ml_lit_review_enabled" in on_argv
    assert on_argv[on_argv.index("--data_scope") + 1] == "15-19"
    assert on_argv[on_argv.index("--health_gate_files") + 1] == "15-19"
    assert on_argv[on_argv.index("--num_iterations") + 1] == "2"


def test_analysis_on_is_bounded_model_aware_and_full_band() -> None:
    config = DataAnalysisWorkflowConfig.model_validate(
        yaml.safe_load((PAIR / "analysis_on.yaml").read_text(encoding="utf-8"))
    )
    assert config.historical_inference_base_asset_id == "tidmad-high-band-validation-input"
    assert config.allow_generated_skill_promotion is True
    assert config.resource_envelope.wall_time_budget_s == 180
    assert config.resource_envelope.sampling_policy.max_items == 10
    assert config.resource_envelope.sampling_policy.strategy == "task_defined"
    assert len(config.available_assets) == 1
    asset = config.available_assets[0]
    assert isinstance(asset.authorized_scope, LegacyPartitionScope)
    assert asset.authorized_scope.data_scope.file_indices == [15, 16, 17, 18, 19]
    assert config.access_policy.allow_model_inference is True
    assert config.access_policy.permits(split_id="validation", information_class="data")
    assert config.declared_scope.raw_input_asset_ids == ("tidmad-high-band-validation-input",)
    assert config.declared_scope.historical_model_asset_ids == ()
    assert not config.access_policy.permits(split_id="validation", information_class="target")
    assert config.access_policy.permits(split_id="validation", information_class="prediction")
    assert not config.access_policy.permits(split_id="validation", information_class="residual")


def test_effectful_pair_launch_refuses_without_frozen_experiment_sha(tmp_path: Path) -> None:
    workspace = tmp_path / "would-be-run"
    result = subprocess.run(
        [
            "bash",
            str(PAIR / "launch_arm.sh"),
            "--arm",
            "on",
            "--siderius-checkout",
            _pair_checkout(),
            "--workspace",
            str(workspace),
            "--data_dir",
            str(tmp_path / "unavailable-real-data"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "effectful launch requires --expected-exp-sha" in result.stderr
    assert not workspace.exists()


def test_pair_launch_refuses_workspace_inside_source_data_even_in_dry_run(tmp_path: Path) -> None:
    """Fails if a run could write generated outputs beneath its raw dataset root."""

    data_root = tmp_path / "raw-data"
    data_root.mkdir()
    workspace = data_root / "run-output"
    result = subprocess.run(
        [
            "bash",
            str(PAIR / "launch_arm.sh"),
            "--arm",
            "on",
            "--siderius-checkout",
            _pair_checkout(),
            "--workspace",
            str(workspace),
            "--data_dir",
            str(data_root),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "workspace must be outside the source data directory" in result.stderr
    assert not workspace.exists()
