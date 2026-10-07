"""Offline final-message parity for explicitly selected historical role replay."""

import json
from copy import deepcopy
from importlib import import_module
from importlib.resources import files
from types import SimpleNamespace

from agent.schemas.ordering import resolve_ordering
from siderius_planner_compat import current_legacy
from siderius_planner_compat.attempt_role_v3 import historical_attempt_role_v3, project_record


def cases():
    return json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/ordering_producer_boundary.json")
        .read_text()
    )["cases"]


def _check_case(case, trial, base):
    raw = deepcopy(case["raw"])
    expected = deepcopy(case["expected_record"])
    completed = raw["status"] in {"success", "failed_mode_collapse"}
    if completed and trial:
        raw["is_trial"] = True
        expected = {**raw, **{key: value for key, value in expected.items() if key not in raw}}
    role = "unresolved" if case["unresolved"] else ("trial" if trial else "formal")
    saved = []
    sandbox = SimpleNamespace(save_record=lambda record: saved.append(deepcopy(record)))
    inputs = SimpleNamespace(
        candidate_id=None,
        experiment_arm=None,
        order_strategy_override="sequential",
        file_order_override=[2, 0, 1],
    )
    ordering = (
        None
        if case["unresolved"]
        else resolve_ordering(
            resolved_scope=[0, 1, 2],
            proposed_strategy="shuffle",
            override_strategy="sequential",
            override_file_order=[2, 0, 1],
        )
    )
    execution = import_module("nodes.ml_hyperparameter_tune_agent.execution")
    execution._emit_attempt_record(
        sandbox,
        raw,
        inputs,
        ordering=ordering,
        refused_before_phase=case["refused_before_phase"],
        attempt_role=role,
    )
    current = saved[0]
    before = deepcopy(current)
    assert current["attempt_role"] == role
    if role != "unresolved":
        assert current["is_trial"] is trial
    assert project_record(current) == expected
    captures = []
    from .attempt_role_v3 import SELECTOR
    from .self_check import _CaptureBridge

    for selector, history in [("legacy-9b78d505cb11-v1", [expected]), (SELECTOR, [current])]:
        bridge = _CaptureBridge()
        bridge.plan(
            **(
                deepcopy(base)
                | {
                    "memory_history": history,
                    "planner_strategy": selector,
                    "current_round": 2,
                    "max_rounds": 4,
                }
            )
        )
        assert len(bridge.captures) == 1
        captures.append(bridge.captures[0])
    assert captures[0] == captures[1], f"Final prompt changed: {case['id']}, trial={trial}"
    assert current == before
    assert historical_attempt_role_v3().identity != current_legacy().identity


def check():
    from agent.prompt_templates.tuner.rendering import TunerTaskRender
    from execute_tools.evaluation_metric import MetricSpec, PresenceScoreabilityContract

    reference = json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/current_legacy_boundary.json")
        .read_text()
    )
    base = reference["base_arguments"] | {
        "task_render": TunerTaskRender.model_validate(reference["task_render"]),
        "metric_spec": MetricSpec.model_validate(
            reference["metric_spec"]
            | {
                "scoreability": PresenceScoreabilityContract.model_validate(
                    reference["metric_spec"]["scoreability"]
                )
            }
        ),
    }
    for case in cases():
        for trial in (False, True):
            _check_case(case, trial, base)
    return {
        "producer_cases": len(cases()),
        "final_prompt_pairs": 2 * len(cases()),
        "api_calls": 0,
        "scope": "controlled raw producer and planner boundary; not full scientific replay",
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
