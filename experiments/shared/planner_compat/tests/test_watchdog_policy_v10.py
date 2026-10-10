"""Historical prompt views must not conceal active native watchdog semantics."""

from copy import deepcopy

import pytest
from siderius_planner_compat.watchdog_policy_v10 import project_record


def _record(*, enabled=False, deadline_policy="budget-ceiling-v1"):
    return {
        "runtime_verification": {
            "runtime_policy": {
                "watchdog": {
                    "enabled": enabled,
                    "grace_seconds": 10.0,
                    "poll_seconds": 1.0,
                    "floor_seconds": 60.0,
                    "safety_factor": None,
                    "max_phase_seconds": None,
                    "deadline_policy": deadline_policy,
                }
            }
        }
    }


@pytest.mark.parametrize(
    ("enabled", "selection"),
    [
        (False, "budget-ceiling-v1"),
        (False, "forecast-tightening-v1"),
        (True, "forecast-tightening-v1"),
    ],
)
def test_only_equivalent_watchdog_metadata_is_removed_on_a_copy(enabled, selection):
    incoming = _record(enabled=enabled, deadline_policy=selection)
    before = deepcopy(incoming)
    expected = deepcopy(incoming)
    expected["runtime_verification"]["runtime_policy"]["watchdog"].pop(
        "deadline_policy"
    )
    assert project_record(incoming) == expected
    assert incoming == before


@pytest.mark.parametrize(
    "record",
    [
        {},
        {"runtime_verification": None},
        {"runtime_verification": {}},
        {"runtime_verification": {"runtime_policy": {}}},
    ],
)
def test_absent_optional_evidence_passes_unchanged(record):
    assert project_record(record) == record


def test_original_six_field_record_passes_unchanged():
    record = _record()
    record["runtime_verification"]["runtime_policy"]["watchdog"].pop("deadline_policy")
    assert project_record(record) == record


@pytest.mark.parametrize(
    "defect",
    [
        "native_enabled",
        "unknown_policy",
        "extra",
        "budget",
        "null_budget",
        "missing_enabled",
        "coerced_enabled",
        "missing_field",
        "invalid_value",
        "partial_budget",
        "watchdog_list",
        "policy_list",
        "verification_list",
    ],
)
def test_unknown_or_nonhistorical_semantics_refuse(defect):
    record = _record()
    policy = record["runtime_verification"]["runtime_policy"]
    watchdog = policy["watchdog"]
    if defect == "native_enabled":
        watchdog["enabled"] = True
    elif defect == "unknown_policy":
        watchdog["deadline_policy"] = "future"
    elif defect == "extra":
        watchdog["future"] = 1
    elif defect in {"budget", "null_budget"}:
        watchdog["budget_seconds"] = 300.0 if defect == "budget" else None
    elif defect == "missing_enabled":
        watchdog.pop("enabled")
    elif defect == "coerced_enabled":
        watchdog["enabled"] = "false"
    elif defect == "missing_field":
        watchdog.pop("grace_seconds")
    elif defect == "invalid_value":
        watchdog["poll_seconds"] = -1
    elif defect == "partial_budget":
        watchdog.pop("deadline_policy")
        watchdog["budget_seconds"] = 300.0
    elif defect == "watchdog_list":
        policy["watchdog"] = []
    elif defect == "policy_list":
        record["runtime_verification"]["runtime_policy"] = []
    else:
        record["runtime_verification"] = []
    before = deepcopy(record)
    with pytest.raises((ValueError, TypeError)):
        project_record(record)
    assert record == before


def test_overlay_preserves_eleven_unit_conditions_and_explicitly_disables_watchdog():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    old = json.loads((root / "paper-epoch-caps-v1.json").read_text())
    new = json.loads((root / "paper-watchdog-v1.json").read_text())
    archived = {
        unit["run_id"]: unit
        for unit in json.loads((root / "paper-replay-369.json").read_text())["units"]
    }
    assert new["launch_parameters"] == old["launch_parameters"] | {
        "--no-runtime_watchdog": True
    }
    assert len(new["covered_units"]) == len(old["covered_units"]) == len(archived) == 11
    for actual, before in zip(new["covered_units"], old["covered_units"], strict=True):
        assert (
            archived[actual["run_id"]]["launch_parameters"]["--no-runtime_watchdog"]
            is True
        )
        expected = deepcopy(before)
        selector = expected["llm_configuration"]["tune"]["planner_strategy"]
        expected["llm_configuration"]["tune"]["planner_strategy"] = selector.replace(
            "epochs-v9", "watchdog-v10"
        )
        assert actual == expected


def test_current_sessions_restore_frozen_policies_without_changing_timing():
    import hashlib
    import json
    from pathlib import Path

    from core.runtime_control.session import WatchdogConfig
    from siderius_planner_compat.runtime_verifier_v8 import (
        project_record as project_verifier,
    )

    from experiments.shared.runtime_compat.replay import replay_cases

    if "deadline_policy" not in WatchdogConfig.model_fields:
        pytest.skip("Selected historical framework predates watchdog policy metadata")
    root = Path(__file__).resolve().parents[2] / "runtime_compat/fixtures"
    traces = json.loads((root / "paper-finite-workloads.json").read_text())
    originals = json.loads((root / "paper-session-policies.json").read_text())
    expected = {row["case_id"]: row for row in originals["cases"]}
    cases = {row["case_id"]: row for row in traces["cases"]}
    sessions = replay_cases(
        traces, completion_policy="verified-prediction-v1", historical_verifier=True
    )
    assert len(sessions) == len(expected) == 23
    for session in sessions:
        frozen = expected[session["case_id"]]
        component = json.dumps(
            session["component"], sort_keys=True, separators=(",", ":")
        )
        assert (
            hashlib.sha256(component.encode()).hexdigest() == frozen["component_sha256"]
        )
        assert (
            session["admission"]
            == cases[session["case_id"]]["expected_archived"]["admission"]
        )
        record = {
            "runtime_verification": {
                "runtime_policy": session["policy"],
                "components": {"training": session["component"]},
                "admission": session["admission"],
            }
        }
        before = deepcopy(record)
        projected = project_record(project_verifier(record))
        assert (
            projected["runtime_verification"]["runtime_policy"]
            == originals["policies"][frozen["policy_index"]]
        )
        assert (
            projected["runtime_verification"]["components"]
            == record["runtime_verification"]["components"]
        )
        assert (
            project_verifier(record) != projected
        )  # v8 alone cannot hide the new field.
        assert record == before


def test_legacy_forecast_only_policy_is_validated_before_metadata_is_removed():
    import json
    from importlib.resources import files

    from agent.planner_strategy import resolve_planner_strategy
    from agent.prompt_templates.tuner.rendering import TunerTaskRender
    from core.runtime_control.session import RuntimeControlPolicy, WatchdogConfig

    if "deadline_policy" not in WatchdogConfig.model_fields:
        pytest.skip("Selected historical framework predates watchdog policy metadata")
    policy = RuntimeControlPolicy(
        runtime_completion_policy="verified-prediction-v1",
        runtime_verifier="legacy-7689fd58-verifier-v1",
        watchdog={"enabled": True, "deadline_policy": "forecast-tightening-v1"},
    ).model_dump(mode="json")
    assert policy["operator_budget_seconds"] is None
    record = {"runtime_verification": {"runtime_policy": policy}}
    before = deepcopy(record)
    expected = deepcopy(record)
    old_policy = expected["runtime_verification"]["runtime_policy"]
    old_policy["watchdog"].pop("deadline_policy")
    for field in (
        "runtime_verifier",
        "runtime_verifier_identity",
        "runtime_completion_policy",
    ):
        old_policy.pop(field)
    fixture = json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/current_legacy_boundary.json")
        .read_text()
    )
    task = TunerTaskRender.model_validate(fixture["task_render"])
    previous = resolve_planner_strategy("legacy-9b78d505cb11-paper-epochs-v9")
    current = resolve_planner_strategy("legacy-9b78d505cb11-paper-watchdog-v10")
    assert current.render_user(
        {"memory_history": [record], "task_render": task}
    ) == previous.render_user({"memory_history": [expected], "task_render": task})
    assert record == before
    with pytest.raises(ValueError, match="changed after run preflight"):
        resolve_planner_strategy(current.identity.name, expected=previous.identity)
    altered = current.identity.model_copy(update={"assembly_sha256": "0" * 64})
    with pytest.raises(ValueError, match="changed after run preflight"):
        resolve_planner_strategy(current.identity.name, expected=altered)


def test_unknown_deadline_owner_refuses_before_rendering(monkeypatch):
    from core.runtime_control.session import WatchdogConfig
    from siderius_planner_compat import watchdog_policy_v10 as owner

    if "deadline_policy" not in WatchdogConfig.model_fields:
        pytest.skip("Selected historical framework predates watchdog policy metadata")
    sources = owner._deadline_sources()
    altered = sources | {
        "watchdog_deadline.py": sources["watchdog_deadline.py"] + b"\n"
    }
    monkeypatch.setattr(owner, "_deadline_sources", lambda: altered)
    with pytest.raises(ValueError, match="deadline source has not been qualified"):
        owner.historical_watchdog_v10()
