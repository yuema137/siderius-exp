"""Comparison retains task Health identity and production invalidation evidence."""

import importlib
import os
from pathlib import Path

import pytest
import yaml
from execute_tools.health_checks import config as health_config
from execute_tools.health_checks import evaluation as health_evaluation
from execute_tools.health_checks.schemas import (
    GateAction,
    GateResult,
    HealthCheckResult,
)


@pytest.fixture
def comparison_run(monkeypatch, tmp_path, bound_tidmad_profile):
    from tasks.tidmad.tools import run_comparison as comparison

    comparison = importlib.reload(comparison)
    assert Path(comparison.SIDERIUS_ROOT) == Path(os.environ["SIDERIUS_CHECKOUT"])
    models = tmp_path / "models"
    models.mkdir()
    calls = []

    class StubSandbox:
        def __init__(self, **kwargs):
            self.dirs = {"models": str(models)}

        def execute_training(self, *, exp_id, **kwargs):
            calls.append("training")
            (models / f"model_punet_{exp_id}_agent.pth").write_bytes(b"stub")
            return {
                "status": "success",
                "results": {
                    "final_loss": 1.0,
                    "loss_history": [1.0],
                    "model_params": {},
                },
            }

        def execute_inference(self, **kwargs):
            return {"status": "success"}

        def save_record(self, record):
            pass

    monkeypatch.setattr(comparison, "TidmadSandbox", StubSandbox)
    monkeypatch.setattr(comparison, "build_sample_set", lambda **kwargs: {0: [0]})
    monkeypatch.setattr(
        comparison, "load_anchor_map", lambda path: {"anchors": {}, "s_max": 1.0}
    )
    monkeypatch.setattr(comparison, "score_vector", lambda **kwargs: ([0.1], 0.1))
    monkeypatch.setattr(comparison, "DATA_DIR", str(tmp_path))
    return comparison, calls


def _observe_policy(tmp_path):
    # Actual generic policy, with runtime failures explicitly observation-only.
    body = yaml.safe_load(Path(health_config.default_health_policy_path()).read_text())
    body["health_policy"]["blocking"]["on_fail"] = "continue"
    path = tmp_path / "observe.yaml"
    path.write_text(yaml.safe_dump(body))
    return path


@pytest.mark.parametrize("passed", [False, True])
def test_observation_only_run_retains_production_invalidation(
    comparison_run, monkeypatch, tmp_path, passed
):
    comparison, calls = comparison_run
    policy = _observe_policy(tmp_path)
    observed = []

    def measured_gate(gate_id, ctx, *, config_path):
        config = health_config.load_health_gates_config(config_path)
        gate = next(g for g in config.health_gates if g.id == gate_id)
        observed.append(gate_id)
        assert gate.on_fail.action == GateAction.CONTINUE
        return GateResult(
            gate_id=gate_id,
            round_index=ctx.round_index,
            passed=passed,
            action=GateAction.CONTINUE,
            check_results=[
                HealthCheckResult(check_name=gate.checks[0].name, passed=passed)
            ],
        )

    monkeypatch.setattr(health_evaluation, "evaluate_gate", measured_gate)
    record = comparison.run_baseline_trial(
        "punet", str(tmp_path / "workspace"), health_checks_config=str(policy)
    )
    production, _, _ = health_config.load_composed_health_config(
        comparison.HEALTH_CHECKS_PATH, comparison.TASK_HEALTH_BINDING
    )
    actions = {g.id: g.on_fail.action for g in production.health_gates}
    assert observed and calls == ["training"]
    persisted = record["health_gate_results"]
    assert {g["gate_name"] for g in persisted} == set(observed)
    expected = {
        g["gate_name"]: not passed and actions[g["gate_name"]] != GateAction.CONTINUE
        for g in persisted
    }
    assert any(expected.values()) == (not passed)
    assert {
        g["gate_name"]: g["would_invalidate_under_production_policy"] for g in persisted
    } == expected
    assert record["gate_action"] == "continue"
    assert record["status"] == ("success" if passed else "failed_mode_collapse")
    assert record["health_config_sha256"]
    effective = health_config.load_health_gates_config(
        str(tmp_path / "workspace/health_checks_effective.yaml")
    )
    assert effective.task_health_binding == "explicit"
    assert len(effective.health_gates) == len(production.health_gates)


@pytest.mark.parametrize("missing", ["TASK_HEALTH_BINDING", "HEALTH_CHECKS_PATH"])
def test_missing_health_inputs_refuse_before_training(
    comparison_run, monkeypatch, tmp_path, missing
):
    comparison, calls = comparison_run
    monkeypatch.setattr(comparison, missing, str(tmp_path / "absent.yaml"))
    with pytest.raises(FileNotFoundError):
        comparison.run_baseline_trial("punet", str(tmp_path / "workspace"))
    assert calls == []


def test_disabled_health_does_not_load_or_invent_checks(
    comparison_run, monkeypatch, tmp_path
):
    comparison, _calls = comparison_run
    monkeypatch.setattr(
        comparison, "TASK_HEALTH_BINDING", str(tmp_path / "absent.yaml")
    )
    record = comparison.run_baseline_trial(
        "punet", str(tmp_path / "workspace"), health_gate_enabled=False
    )
    assert record["health_gate_results"] == []
    assert record["health_gate_enabled"] is False
    assert not (tmp_path / "workspace/health_checks_effective.yaml").exists()


def test_changed_task_roster_changes_effective_identity_and_refuses_workspace_reuse(
    comparison_run, monkeypatch, tmp_path
):
    comparison, _calls = comparison_run
    first, sha = health_config.materialize_effective_config(
        None,
        None,
        str(tmp_path / "original"),
        task_health_binding=comparison.TASK_HEALTH_BINDING,
    )
    task = yaml.safe_load(Path(comparison.TASK_HEALTH_BINDING).read_text())
    task["roster"][0]["parameters"]["min_unique_int8_values"] += 1
    changed = tmp_path / "changed-health.yaml"
    changed.write_text(yaml.safe_dump(task))
    _, changed_sha = health_config.materialize_effective_config(
        None,
        None,
        str(tmp_path / "changed"),
        task_health_binding=str(changed),
    )
    assert sha != changed_sha
    with pytest.raises(ValueError):
        health_config.materialize_effective_config(
            None,
            None,
            str(Path(first).parent),
            task_health_binding=str(changed),
        )


@pytest.mark.parametrize("change", ["threshold", "gate_id"])
def test_precomposed_old_rules_refuse_before_training(
    comparison_run, monkeypatch, tmp_path, change
):
    comparison, calls = comparison_run
    old_effective, old_sha = health_config.materialize_effective_config(
        str(_observe_policy(tmp_path)),
        None,
        str(tmp_path / "workspace"),
        task_health_binding=comparison.TASK_HEALTH_BINDING,
    )
    task = yaml.safe_load(Path(comparison.TASK_HEALTH_BINDING).read_text())
    if change == "threshold":
        task["roster"][0]["parameters"]["min_unique_int8_values"] += 10
    else:
        task["roster"][0]["gate_id"] = "changed-diversity-check"
    changed = tmp_path / "changed-health.yaml"
    changed.write_text(yaml.safe_dump(task))
    monkeypatch.setattr(comparison, "TASK_HEALTH_BINDING", str(changed))
    with pytest.raises(ValueError, match="runtime Health checks differ"):
        comparison.run_baseline_trial(
            "punet",
            str(tmp_path / "workspace"),
            health_checks_config=old_effective,
            health_config_sha256=old_sha,
        )
    assert calls == []
