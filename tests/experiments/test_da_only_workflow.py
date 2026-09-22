"""DA-only must reach the native chain without legacy model advice."""

from pathlib import Path

import pytest

from experiments.tidmad.information_treatments import frozen_prior
from experiments.tidmad.information_treatments.prepare_full import prepare_full
from experiments.tidmad.main_fixed_workflow import preflight
from experiments.tidmad.main_fixed_workflow.full_binding import FullAnalysisInputs

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("band", ["0-3", "4-9", "10-14", "15-19"])
def test_da_only_prepares_and_launches_without_loading_model_advice(
    tmp_path, monkeypatch, band
):
    original = frozen_prior.FrozenArtifact.verify

    def verify(self, root):
        if self.path.endswith("advice.json"):
            pytest.fail("DA-only attempted to load model advice")
        return original(self, root)

    monkeypatch.setattr(frozen_prior.FrozenArtifact, "verify", verify)
    prepared = prepare_full(ROOT, band, tmp_path / "binding", model_advice=False)
    assert prepared["advice_path"] is None and prepared["advice_sha256"] is None
    binding = FullAnalysisInputs(
        policy_path=prepared["analysis_policy_path"],
        policy_sha256=prepared["analysis_policy_sha256"],
        composition_path=prepared["composition_path"],
        model_advice=False,
    )
    checkout = tmp_path / "infra"
    launcher = checkout / "scripts/launch/run_chain.sh"
    launcher.parent.mkdir(parents=True)
    launcher.touch()
    monkeypatch.setattr(preflight, "verify_framework_pin", lambda *_: "a" * 40)
    monkeypatch.setattr(preflight, "verify_installed_framework", lambda *_: None)
    monkeypatch.setattr(preflight, "verify_band_inputs", lambda *_: {"band": band})
    checks = []
    monkeypatch.setattr(preflight, "require_generated_analysis_runtime", checks.append)
    arguments = {
        "band": band,
        "data_dir": tmp_path / "data",
        "workspace": tmp_path / "work",
        "run_name": "da-only",
    }
    on = preflight.resolve_full_launch(
        ROOT, checkout, full_analysis=binding, **arguments
    )
    off = preflight.resolve_no_prior_launch(ROOT, checkout, **arguments)
    assert checks == [checkout]
    assert on["version"] == "tidmad-main-fixed-da-only-preflight-v1"
    assert on["analysis_binding"]["model_advice"] is False
    assert on["treatment"]["advice"]["mode"] == "disabled"
    assert "--advice" not in on["command"] and "--advice_sha256" not in on["command"]
    assert "--data_analysis_enabled" in on["command"]
    assert "--no-data_analysis_enabled" in off["command"]
    assert "--ml_lit_review_enabled" in on["command"]
    for key in ("workflow_sha256", "llm_config_sha256", "task_package_tree", "data"):
        assert on[key] == off[key]
    for flag in (
        "--trial_time_budget_minutes",
        "--formal_time_budget_minutes",
        "--max_epochs",
        "--formal_eval_portion",
        "--training_validation_portion",
    ):
        assert (
            on["command"][on["command"].index(flag) + 1]
            == off["command"][off["command"].index(flag) + 1]
        )


def test_supervisor_cli_carries_da_only_condition_without_launch(monkeypatch, tmp_path):
    import sys

    from experiments.tidmad.main_fixed_workflow import supervisor

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "supervisor",
            "--condition",
            "da-only",
            "--siderius-checkout",
            str(tmp_path / "infra"),
            "--band",
            "0-3",
            "--data_dir",
            str(tmp_path / "data"),
            "--unit-dir",
            str(tmp_path / "unit"),
            "--run_name",
            "da-only",
            "--analysis-policy",
            str(tmp_path / "policy.yaml"),
            "--analysis-policy-sha256",
            "a" * 64,
            "--analysis-composition",
            str(tmp_path / "composition.yaml"),
        ],
    )
    calls = []
    monkeypatch.setattr(
        supervisor, "run_unit", lambda **kwargs: calls.append(kwargs) or 0
    )
    assert supervisor.main() == 0
    assert calls[0]["full_analysis"].model_advice is False
    assert calls[0]["launch"] is False
