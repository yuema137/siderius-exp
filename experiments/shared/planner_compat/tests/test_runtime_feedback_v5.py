"""Versioned runtime feedback restores final prompts without modifying raw facts."""

import json
from copy import deepcopy
from importlib.resources import files

import pytest
from siderius_planner_compat.runtime_feedback_v5 import LEGACY_UPDATE, project_record
from siderius_planner_compat.self_check import _CaptureBridge


def raw_record():
    # Captured at the declared infra revision from its real refusal producer.
    # Producer-to-next-planner propagation is owned by the infra integration
    # test; exp consumes the recorded boundary, not a private node function.
    fixture = json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/runtime_feedback_producer.json")
        .read_text()
    )
    record = fixture["record"]
    # Persistence stamps the resolved role; the runtime sidecar has its own
    # timestamp. Exercise the full typed-history path through inherited v3.
    record["attempt_role"] = "trial"
    record["is_trial"] = True
    record["runtime_verification"]["timestamp"] = record["timestamp"]
    return record


def base_arguments():
    from agent.prompt_templates.tuner.rendering import TunerTaskRender
    from agent.skills.check_config_format_skill.wrapper import run_skill
    from execute_tools.evaluation_metric import MetricSpec, PresenceScoreabilityContract

    fixture = json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/current_legacy_boundary.json")
        .read_text()
    )
    return fixture["base_arguments"] | {
        "config_manual": run_skill(None)["data"],
        "task_render": TunerTaskRender.model_validate(fixture["task_render"]),
        "metric_spec": MetricSpec.model_validate(
            fixture["metric_spec"]
            | {
                "scoreability": PresenceScoreabilityContract.model_validate(
                    fixture["metric_spec"]["scoreability"]
                )
            }
        ),
    }


@pytest.mark.parametrize("late", [False, True])
def test_final_request_matches_v4_with_frozen_old_feedback(late):
    current = raw_record()
    expected = deepcopy(current)
    expected["memory"].pop("runtime_feedback_version")
    expected["memory"]["memory_update"] = LEGACY_UPDATE
    before = deepcopy(current)
    prefix = "legacy-9b78d505cb11-paper" + ("-late" if late else "")
    captures = []
    for strategy, record in [
        (prefix + "-v4", expected),
        (prefix + "-runtime-v5", current),
    ]:
        bridge = _CaptureBridge()
        bridge.plan(
            **(
                base_arguments()
                | {"planner_strategy": strategy, "memory_history": [record]}
            )
        )
        captures.append(bridge.captures)
    assert captures[0] == captures[1]
    # Ensure this witness actually exercises the changed wording, independently
    # of the new marker. An unchanged archival fixture alone would miss drift.
    factual = deepcopy(current)
    factual["memory"].pop("runtime_feedback_version")
    unconverted = _CaptureBridge()
    unconverted.plan(
        **(
            base_arguments()
            | {"planner_strategy": prefix + "-v4", "memory_history": [factual]}
        )
    )
    assert unconverted.captures != captures[0]
    assert current == before
    assert project_record(current) == expected
    assert project_record(expected) == expected


@pytest.mark.parametrize(
    "change", ["version", "status", "stage", "admission", "within_budget", "record_only", "pre_launch"]
)
def test_unknown_or_inconsistent_producers_fail_instead_of_guessing(change):
    record = raw_record()
    if change == "version":
        record["memory"]["runtime_feedback_version"] = "future-v2"
    elif change == "status":
        record["status"] = "success"
    elif change == "stage":
        record["memory"]["verification_stage"] = "preflight"
    elif change in {"within_budget", "record_only"}:
        record["runtime_verification"]["admission"]["reason_code"] = change
    elif change == "pre_launch":
        record["runtime_verification"]["admission"]["stage"] = "pre_launch_screen"
    else:
        record["runtime_verification"]["admission"]["decision"] = "admitted"
    with pytest.raises(ValueError):
        project_record(record)


@pytest.mark.parametrize(
    ("stage", "reason_code"),
    [
        ("post_setup_runtime_verification", None),
        ("post_training_verification", "budget_exceeded"),
        ("training_allocation.training", "training_allocation_exceeded"),
    ],
)
def test_supported_refusals_keep_final_historical_messages(stage, reason_code):
    record = raw_record()
    record["runtime_verification"]["admission"].update(
        stage=stage, reason_code=reason_code
    )
    expected = deepcopy(record)
    expected["memory"].pop("runtime_feedback_version")
    expected["memory"]["memory_update"] = LEGACY_UPDATE
    captures = []
    for strategy, history in [
        ("legacy-9b78d505cb11-paper-v4", expected),
        ("legacy-9b78d505cb11-paper-runtime-v5", record),
    ]:
        bridge = _CaptureBridge()
        bridge.plan(
            **(base_arguments() | {"planner_strategy": strategy, "memory_history": [history]})
        )
        captures.append(bridge.captures)
    assert captures[0] == captures[1]
    assert record["memory"]["runtime_feedback_version"] == "facts-v1"
