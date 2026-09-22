"""Prevent the strategy-only switch from reintroducing either legacy prior."""

import hashlib
from pathlib import Path

import pytest
import yaml

from experiments.tidmad.main_orchestrator import prepare as preparation
from experiments.tidmad.main_orchestrator.policy import Prior
from experiments.tidmad.main_orchestrator.public_composition import (
    public_candidate_composition,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("band", ["0-3", "4-9", "10-14", "15-19"])
def test_strategy_only_preparation_keeps_no_prior_binding(tmp_path, monkeypatch, band):
    """Fail if preparation reads Full material or changes execution/model routing."""
    from execute_tools.task_registration_scope import run_registration_scope

    monkeypatch.setattr(preparation, "verify_framework_pin", lambda *_: "a" * 40)
    monkeypatch.setattr(preparation, "verify_installed_framework", lambda *_: None)
    # Native composition is real; only pin/environment inspection is bypassed here.
    import json

    from experiments.tidmad.main_orchestrator.execution_policy import ExecutionPolicy

    raw = json.loads(
        (ROOT / "experiments/tidmad/main_fixed_workflow/workflow.json").read_text()
    )["parameters"]
    policy = ExecutionPolicy.model_validate(
        {
            key: (
                ("--runtime_watchdog" in raw)
                if key == "runtime_watchdog"
                else raw["--" + key]
            )
            for key in ExecutionPolicy.model_fields
        }
    )
    monkeypatch.setattr(
        preparation, "resolve_execution_policy", lambda *_: (policy, "same-workflow")
    )
    monkeypatch.setattr(
        preparation,
        "candidate_analysis_policy",
        lambda *_: pytest.fail("loaded DA policy"),
    )
    from workflows import run_one_iteration

    monkeypatch.setattr(
        run_one_iteration,
        "load_advice_artifact",
        lambda *_a, **_kw: pytest.fail("loaded model advice"),
    )
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
            strategy_only=True,
        )
    for key in (
        "fixed_information_authority",
        "execution_policy",
        "agent_models_sha256",
        "data_scope",
        "composition_fingerprint",
    ):
        assert on[key] == off[key]
    assert on["condition"] == "O-StrategyOnly"
    assert (
        not on["data_analysis_enabled"] and not on["native_analysis_binding_resolved"]
    )
    assert on["advice_by_recipient"] == {}
    assert not on["model_advice_enabled"]
    assert not (tmp_path / "on/advice.json").exists()
    assert not (tmp_path / "on/analysis-policy.yaml").exists()
    assert yaml.safe_load((tmp_path / "on/composition.yaml").read_text())[
        "data_analysis"
    ] == {"enabled": False}
    source = (
        ROOT
        / "experiments/tidmad/information_treatments/controller-work-strategy-v3.md"
    )
    assert (
        tmp_path / "on/controller-work-strategy.md"
    ).read_bytes() == source.read_bytes()
    assert (
        on["controller_strategy_advice"]["sha256"]
        == hashlib.sha256(source.read_bytes()).hexdigest()
    )


def test_strategy_only_refuses_full_before_creating_output(tmp_path):
    """Catch the legacy joint switch accidentally overriding DA-off."""
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="strategy-only requires prior off"):
        preparation.prepare(
            ROOT, tmp_path, output, prior=Prior.ON, band="0-3", strategy_only=True
        )
    assert not output.exists()


@pytest.mark.parametrize("band", ["0-3", "4-9", "10-14", "15-19"])
def test_native_public_binding_cannot_enable_analysis(tmp_path, band):
    """Exercise native refusal, not just the disabled JSON field or a prompt."""
    from core.generated_library import bind_generated_library_to_workspace
    from execute_tools.task_registration_scope import run_registration_scope
    from workflows.task_composition import compose_run_task_bindings

    from experiments.tidmad.information_treatments.frozen_prior import (
        full_analysis_policy,
    )

    bind_generated_library_to_workspace(tmp_path / "state")
    analysis = tmp_path / "analysis.yaml"
    analysis.write_text(
        yaml.safe_dump(full_analysis_policy(ROOT, band).model_dump(mode="json"))
    )
    manifest = tmp_path / "public.yaml"
    manifest.write_text(yaml.safe_dump(public_candidate_composition(ROOT)))
    with run_registration_scope():
        bindings = compose_run_task_bindings(str(manifest))
        assert bindings.data_analysis is None
        assert bindings.metric.spec.id == "tidmad_denoising_score"
    # Even supplying a valid Full policy cannot give the deployed compact data
    # path an analysis capability; private loss/evaluation stay separate routes.
    manifest.write_text(yaml.safe_dump(public_candidate_composition(ROOT, analysis)))
    with (
        run_registration_scope(),
        pytest.raises(ValueError, match="does not implement TaskAnalysisCapability"),
    ):
        compose_run_task_bindings(str(manifest))
