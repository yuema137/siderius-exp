"""The smoke driver runs the tuner under the declared bounds, not API defaults.

* ``test_the_smoke_input_carries_the_fixed_workflow_bounds`` — every
  execution bound in the input equals the fixed workflow's `workflow.json`
  value, so the orchestrated condition cannot drift from `nop_004` by a
  default nobody chose; only the epoch budget is the smoke's own.
* ``test_the_smoke_input_routes_every_role_to_the_declared_model`` — the
  planner and reflector both use the run declaration's routing; the schema
  default is a different provider entirely.
"""

from __future__ import annotations

import json
from pathlib import Path

from experiments.phyts_tess.main_orchestrator.smoke_tuner import build_smoke_input

EXP_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = EXP_ROOT / "experiments/phyts_tess/main_fixed_workflow/workflow.json"


def _input(tmp_path: Path):
    return build_smoke_input(
        run_id="onp_smoke_test",
        storage_workspace=tmp_path / "work",
        data_dir=tmp_path / "rundata",
        task_description="regress frot",
        task_composition_ref=None,
        model_type="tess_reference_cnn",
        max_epochs=2,
        rounds=2,
    )


def test_the_smoke_input_carries_the_fixed_workflow_bounds(tmp_path):
    agent_input = _input(tmp_path)
    parameters = json.loads(WORKFLOW.read_text())["parameters"]

    for flag in (
        "trial_time_budget_minutes",
        "formal_time_budget_minutes",
        "trial_vram_budget_gb",
        "formal_vram_budget_gb",
        "formal_training_scope_source",
        "formal_portion",
        "formal_train_portion",
        "formal_eval_portion",
        "training_budget_reserve_fraction",
    ):
        assert getattr(agent_input, flag) == parameters[f"--{flag}"], flag
    assert agent_input.runtime_watchdog_enabled is False
    assert agent_input.max_rounds == 2 and agent_input.plan_overrides == {
        "is_trial": True
    }
    assert (
        agent_input.max_epochs,
        agent_input.trial_max_epochs,
        agent_input.formal_max_epochs,
    ) == (2, 2, 2)
    assert (
        agent_input.healthgate_mode == "blocking"
        and agent_input.result_authority == "scientific"
    )
    assert agent_input.storage.local is not None
    assert agent_input.storage.local.run_name == "onp_smoke_test"


def test_the_smoke_input_routes_every_role_to_the_declared_model(tmp_path):
    agent_input = _input(tmp_path)
    assert (agent_input.llm_provider, agent_input.llm_model_id) == (
        "openai",
        "gpt-5.6-sol",
    )
    assert (agent_input.reflect_provider, agent_input.reflect_model_id) == (
        "openai",
        "gpt-5.6-sol",
    )
    assert (
        agent_input.reasoning_effort == agent_input.reflect_reasoning_effort == "medium"
    )


def test_a_missing_provider_credential_stops_the_driver_before_any_call(
    tmp_path, monkeypatch
):
    """The first smoke launch ran with an empty key and burned its whole
    attempt budget on 401s in under a minute; the check happens before the
    framework is even imported."""
    from experiments.phyts_tess.main_orchestrator.smoke_tuner import main

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import pytest

    with pytest.raises(SystemExit, match="OPENAI_API_KEY is not set"):
        main(
            [
                "--workspace",
                str(tmp_path),
                "--run-id",
                "onp_smoke_test",
                "--storage-root",
                str(tmp_path),
                "--composition",
                str(tmp_path / "c.yaml"),
                "--data-dir",
                str(tmp_path),
                "--deadline-epoch",
                "4102444800",
            ]
        )
