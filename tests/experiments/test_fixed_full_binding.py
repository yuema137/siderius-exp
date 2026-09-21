"""Full may add approved analysis; it cannot swap scientific task or band access."""

from pathlib import Path

import pytest
import yaml

from experiments.shared.checksum_manifest import sha256_file
from experiments.tidmad.information_treatments.prior_binding import (
    candidate_analysis_policy,
    composition_overlay,
)
from experiments.tidmad.main_fixed_workflow.full_binding import (
    verify_full_analysis_binding,
)

ROOT = Path(__file__).resolve().parents[2]


def test_full_binding_accepts_bound_candidate_and_refuses_policy_or_task_drift(
    tmp_path,
):
    policy = candidate_analysis_policy(ROOT, "0-3")
    policy_path = tmp_path / "analysis.yaml"
    policy_path.write_text(yaml.safe_dump(policy.model_dump(mode="json")))
    composition_path = tmp_path / "composition.yaml"
    composition = composition_overlay(ROOT, policy_path)
    composition_path.write_text(yaml.safe_dump(composition))
    kwargs = {
        "band": "0-3",
        "policy_path": policy_path,
        "policy_sha256": sha256_file(policy_path),
        "composition_path": composition_path,
    }
    receipt = verify_full_analysis_binding(ROOT, **kwargs)
    assert receipt["composition_sha256"] == sha256_file(composition_path)
    with pytest.raises(ValueError, match="input-only boundary"):
        verify_full_analysis_binding(ROOT, **{**kwargs, "band": "4-9"})
    with pytest.raises(ValueError, match="explicitly bound digest"):
        verify_full_analysis_binding(ROOT, **{**kwargs, "policy_sha256": "0" * 64})
    composition["metric"]["declaration"] = "/some/other/metric.json"
    composition_path.write_text(yaml.safe_dump(composition))
    with pytest.raises(ValueError, match="frozen task"):
        verify_full_analysis_binding(ROOT, **kwargs)


def test_full_preflight_enables_prior_without_changing_shared_workflow(
    monkeypatch, tmp_path
):
    from experiments.tidmad.main_fixed_workflow import preflight
    from experiments.tidmad.main_fixed_workflow.full_binding import FullAnalysisInputs

    monkeypatch.setattr(preflight, "verify_framework_pin", lambda *_: "a" * 40)
    monkeypatch.setattr(preflight, "verify_installed_framework", lambda *_: None)
    monkeypatch.setattr(preflight, "verify_band_inputs", lambda *_: {"band": "0-3"})
    checkout = tmp_path / "infra"
    launcher = checkout / "scripts/launch/run_chain.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/bash\n")
    policy_path = tmp_path / "analysis.yaml"
    policy_path.write_text(
        yaml.safe_dump(candidate_analysis_policy(ROOT, "0-3").model_dump(mode="json"))
    )
    composition_path = tmp_path / "composition.yaml"
    composition_path.write_text(yaml.safe_dump(composition_overlay(ROOT, policy_path)))
    binding = FullAnalysisInputs(
        policy_path=policy_path,
        policy_sha256=sha256_file(policy_path),
        composition_path=composition_path,
    )
    kwargs = {
        "band": "0-3",
        "data_dir": tmp_path / "data",
        "workspace": tmp_path / "workspace",
        "run_name": "explicit-full-preview",
    }
    full = preflight.resolve_full_launch(
        ROOT, checkout, full_analysis=binding, **kwargs
    )
    no_prior = preflight.resolve_no_prior_launch(ROOT, checkout, **kwargs)
    command = full["command"]
    assert command.count("--task_composition") == 1
    assert command[command.index("--task_composition") + 1] == str(composition_path)
    assert "--data_analysis_enabled" in command
    assert "--no-data_analysis_enabled" not in command
    assert "--advice" in command and "--advice_sha256" in command
    assert full["analysis_binding"]["analysis_policy_sha256"] == binding.policy_sha256
    assert "analysis_binding" not in no_prior
    for flag in [
        "--formal_time_budget_minutes",
        "--trial_time_budget_minutes",
        "--formal_train_portion",
        "--formal_eval_portion",
        "--training_validation_portion",
        "--max_epochs",
        "--formal_vram_budget_gb",
        "--workflow_parameter_rules",
        "--llm_config",
    ]:
        assert (
            command[command.index(flag) + 1]
            == no_prior["command"][no_prior["command"].index(flag) + 1]
        )
    assert command[command.index("--training_validation_portion") + 1] == "0.1"
    assert command[command.index("--formal_eval_portion") + 1] == "1.0"
    policy_path.write_text(policy_path.read_text() + "\n# changed after binding\n")
    with pytest.raises(ValueError, match="bound digest"):
        preflight.resolve_full_launch(ROOT, checkout, full_analysis=binding, **kwargs)
