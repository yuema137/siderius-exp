"""DA-only adds analysis while preserving NoPrior execution and advice exclusion."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from experiments.tidmad.main_orchestrator import prepare as preparation
from experiments.tidmad.main_orchestrator.execution_policy import ExecutionPolicy
from experiments.tidmad.main_orchestrator.policy import Prior

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("band", ["0-3", "4-9", "10-14", "15-19"])
def test_da_only_preserves_no_prior_except_analysis(tmp_path, monkeypatch, band):
    from execute_tools.task_registration_scope import run_registration_scope
    from workflows import run_one_iteration

    monkeypatch.setattr(preparation, "verify_framework_pin", lambda *_: "a" * 40)
    monkeypatch.setattr(preparation, "verify_installed_framework", lambda *_: None)
    raw = json.loads(
        (ROOT / "experiments/tidmad/main_fixed_workflow/workflow.json").read_text()
    )["parameters"]
    policy = ExecutionPolicy.model_validate(
        {
            key: ("--runtime_watchdog" in raw)
            if key == "runtime_watchdog"
            else raw["--" + key]
            for key in ExecutionPolicy.model_fields
        }
    )
    monkeypatch.setattr(
        preparation, "resolve_execution_policy", lambda *_: (policy, "same-workflow")
    )
    monkeypatch.setattr(
        preparation,
        "materialize_controller_strategy",
        lambda *_a, **_kw: pytest.fail("read workflow strategy"),
    )
    monkeypatch.setattr(
        run_one_iteration,
        "load_advice_artifact",
        lambda *_a, **_kw: pytest.fail("read model advice"),
    )

    def task_hashes():
        return {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "tasks/tidmad").rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }

    before = task_hashes()
    with run_registration_scope():
        off = preparation.prepare(
            ROOT, tmp_path / "infra", tmp_path / "off", prior=Prior.OFF, band=band
        )
    with run_registration_scope():
        on = preparation.prepare(
            ROOT,
            tmp_path / "infra",
            tmp_path / "on",
            prior=Prior.OFF,
            band=band,
            data_analysis_only=True,
        )
    assert task_hashes() == before
    for key in (
        "execution_policy",
        "execution_policy_sha256",
        "fixed_workflow_sha256",
        "agent_models_sha256",
        "data_scope",
        "literature_review_enabled",
    ):
        assert on[key] == off[key]
    off_manifest = yaml.safe_load((tmp_path / "off/composition.yaml").read_text())
    on_manifest = yaml.safe_load((tmp_path / "on/composition.yaml").read_text())
    assert off_manifest.pop("data_analysis") == {"enabled": False}
    assert on_manifest.pop("data_analysis")["enabled"] is True
    assert on_manifest == off_manifest
    assert on["condition"] == "O-DAOnly"
    assert on["analysis_policy_status"] == "frozen_da_only_v1"
    assert on["data_analysis_enabled"] and on["native_analysis_binding_resolved"]
    assert not on["model_advice_enabled"]
    assert on["advice_by_recipient"] == {}
    assert on["advice_sha256"] is None
    assert on["controller_strategy_advice"] is None
    assert "prompt_supplement" not in on
    for forbidden in (
        "advice.json",
        "controller-work-strategy.md",
        "prompt-supplement.json",
    ):
        assert not (tmp_path / "on" / forbidden).exists()
    from experiments.tidmad.information_treatments.prior_binding import (
        candidate_analysis_policy,
    )

    assert yaml.safe_load((tmp_path / "on/analysis-policy.yaml").read_text()) == (
        candidate_analysis_policy(ROOT, band).model_dump(mode="json")
    )
    assert not on["launch_ready"]


@pytest.mark.parametrize(
    "prior,strategy", [(Prior.ON, False), (Prior.OFF, True), (Prior.ON, True)]
)
def test_da_only_rejects_conflicting_treatments_before_writing(
    tmp_path, prior, strategy
):
    output = tmp_path / "output"
    with pytest.raises(
        ValueError, match="data-analysis-only requires prior off and strategy off"
    ):
        preparation.prepare(
            ROOT,
            tmp_path,
            output,
            prior=prior,
            band="0-3",
            data_analysis_only=True,
            strategy_only=strategy,
        )
    assert not output.exists()
