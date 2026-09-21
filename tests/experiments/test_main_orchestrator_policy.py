"""Catch joint-treatment leakage and band/profile mismatch at real native binding."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from experiments.tidmad.main_orchestrator.policy import (
    CONTROLLER_STRATEGY_RELATIVE_PATH,
    CONTROLLER_STRATEGY_SHA256,
    Prior,
    candidate_analysis_policy,
    composition_overlay,
    materialize_controller_strategy,
    resolve_prior,
)
from experiments.tidmad.main_orchestrator.prepare import deployment_status

ROOT = Path(__file__).resolve().parents[2]


def test_deployment_status_matches_the_frozen_joint_treatment():
    """Prevent a frozen Full policy from reverting to candidate launch metadata."""
    full_status, full_blockers = deployment_status(Prior.ON)
    off_status, off_blockers = deployment_status(Prior.OFF)

    assert full_status == "frozen_full_v7"
    assert off_status == "disabled"
    assert all("Review/freeze" not in blocker for blocker in full_blockers)
    assert any("frozen Full analysis policy" in blocker for blocker in full_blockers)
    assert all("controller strategy" not in blocker for blocker in off_blockers)


def test_controller_strategy_is_content_pinned_and_materialized_separately(tmp_path):
    """Catch stale strategy bytes or accidental routing as the model advice file."""
    output = tmp_path / "full"
    output.mkdir()
    binding = materialize_controller_strategy(ROOT, output)

    source = ROOT / CONTROLLER_STRATEGY_RELATIVE_PATH
    destination = output / "controller-work-strategy.md"
    assert destination.read_bytes() == source.read_bytes()
    assert binding.receipt() == {
        "artifact": "controller-work-strategy.md",
        "sha256": CONTROLLER_STRATEGY_SHA256,
        "recipients": ["outer_controller"],
        "layering": "on_top_of_model_research_advice",
    }
    assert not (output / "advice.json").exists()


def test_controller_strategy_refuses_unreviewed_content_change(tmp_path):
    """Catch strategy edits that bypass the explicit frozen digest update."""
    source = tmp_path / CONTROLLER_STRATEGY_RELATIVE_PATH
    source.parent.mkdir(parents=True)
    source.write_text("changed without review\n")
    output = tmp_path / "output"
    output.mkdir()

    with pytest.raises(ValueError, match="controller strategy checksum mismatch"):
        materialize_controller_strategy(tmp_path, output)


@pytest.mark.parametrize(
    "band,indices",
    [
        ("0-3", [0, 1, 2, 3]),
        ("4-9", [4, 5, 6, 7, 8, 9]),
        ("10-14", [10, 11, 12, 13, 14]),
        ("15-19", [15, 16, 17, 18, 19]),
    ],
)
def test_both_prior_states_resolve_native_binding_without_changing_task(
    tmp_path, band, indices
):
    # Operator preparation runs in its own process. A prior public-package test
    # may have registered the same task ID under a different package identity;
    # preserve the registry's refusal rather than clearing or weakening it.
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            """
import json, runpy, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
module = runpy.run_path(sys.argv[2])
module['_check_prior_bindings'](Path(sys.argv[3]), sys.argv[4], json.loads(sys.argv[5]))
""",
            str(ROOT),
            str(Path(__file__).resolve()),
            str(tmp_path),
            band,
            json.dumps(indices),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _check_prior_bindings(tmp_path, band, indices):
    # Would fail if task-path ID, profile pin or selected band drifted from the frozen-pool binding.
    from core.generated_library import bind_generated_library_to_workspace

    bind_generated_library_to_workspace(str(tmp_path / "state"))
    from workflows.task_composition import compose_run_task_bindings

    before = {
        p: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "tasks/tidmad").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    policy = candidate_analysis_policy(ROOT, band)
    config = tmp_path / "analysis.yaml"
    config.write_text(yaml.safe_dump(policy.model_dump(mode="json")))
    baseline = None
    for prior in (Prior.OFF, Prior.ON):
        treatment = resolve_prior(ROOT, prior)
        payload = composition_overlay(ROOT, config if prior is Prior.ON else None)
        shared = {k: v for k, v in payload.items() if k != "data_analysis"}
        if baseline is None:
            baseline = shared
        assert shared == baseline
        path = tmp_path / f"{prior}.yaml"
        path.write_text(yaml.safe_dump(payload))
        binding = compose_run_task_bindings(str(path))
        if prior is Prior.ON:
            assert treatment.advice_path is not None
            analysis = binding.data_analysis
            assert analysis is not None
            asset = analysis.available_assets[0]
            assert asset.authorized_scope.data_scope.resolve(20) == indices
            assert asset.location.task_data_path_id == "tidmad_frozen_training_pool"
            assert all(
                not r.targets_visible
                and not r.predictions_visible
                and not r.residuals_visible
                for r in analysis.access_policy.split_rules
            )
        else:
            assert binding.data_analysis is None
            assert treatment.advice_path is None
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}


@pytest.mark.parametrize("mutation", ["analysis_only", "advice_only", "bad_digest"])
def test_partial_or_corrupt_full_treatment_is_rejected(tmp_path, mutation):
    # An arm label must not hide a missing prior component or stale advice bytes.
    (tmp_path / "tasks/tidmad").mkdir(parents=True)
    rel = Path("experiments/tidmad/information_treatments/main-fixed-full.yaml")
    (tmp_path / rel.parent).mkdir(parents=True)
    raw = yaml.safe_load((ROOT / rel).read_text())
    advice = Path(raw["advice"]["artifact"])
    (tmp_path / advice.parent).mkdir(parents=True)
    shutil.copyfile(ROOT / advice, tmp_path / advice)
    if mutation == "analysis_only":
        raw["advice"] = {"mode": "disabled"}
    elif mutation == "advice_only":
        raw["modules"]["data_analysis"]["siderius"] = "disabled"
    else:
        raw["advice"]["sha256"] = "0" * 64
    (tmp_path / rel).write_text(yaml.safe_dump(raw))
    with pytest.raises(ValueError):
        resolve_prior(tmp_path, Prior.ON)
