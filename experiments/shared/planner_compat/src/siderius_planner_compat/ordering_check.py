"""Offline producer and final-message checks for the explicit ordering-v2 provider.

Run from a qualified infra checkout's frozen environment with this package installed.
No provider calls, datasets or training. The reference fixture was emitted by the
pre-#447 checkout; this command never regenerates that oracle.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from copy import deepcopy
from importlib.resources import files
from types import SimpleNamespace

from agent.planner_strategy import resolve_planner_strategy
from agent.prompt_templates.tuner.rendering import TunerTaskRender
from agent.schemas.ordering import resolve_ordering
from execute_tools.evaluation_metric import MetricSpec, PresenceScoreabilityContract

from .ordering_v2 import SELECTOR, project_record
from .self_check import _CaptureBridge


def emit_case(case):
    """Exercise infra's actual current validate-and-save boundary."""
    execution = importlib.import_module("nodes.ml_hyperparameter_tune_agent.execution")
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
    execution._emit_attempt_record(
        sandbox,
        deepcopy(case["raw"]),
        inputs,
        ordering=ordering,
        refused_before_phase=case["refused_before_phase"],
    )
    assert len(saved) == 1
    return saved[0]


def check():
    fixture = json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/ordering_producer_boundary.json")
        .read_text()
    )
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
    pairs = []
    histories = []
    for case in fixture["cases"]:
        current = emit_case(case)
        before = deepcopy(current)
        projected = project_record(current)
        expected = case["expected_record"]
        if json.dumps(projected) != json.dumps(expected):
            raise AssertionError(f"Producer representation changed: {case['id']}")
        if current != before or "ordering_observation" not in current:
            raise AssertionError("Projection modified the persisted source")
        histories.append((case["id"], [expected], [current]))
    # Both compatibility directions plus window compaction across mixed inputs.
    old_records = [case["expected_record"] for case in fixture["cases"]]
    new_records = [emit_case(case) for case in fixture["cases"]]
    histories.extend(
        [
            ("old-only", old_records, deepcopy(old_records)),
            ("mixed-window", old_records * 2, old_records + new_records),
        ]
    )
    for name, old, new in histories:
        captures = []
        for selector, history in [("legacy-9b78d505cb11-v1", old), (SELECTOR, new)]:
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
        if captures[0] != captures[1]:
            raise AssertionError(f"Final historical prompt changed: {name}")
        pairs.append(
            {
                "id": name,
                "system_sha256": hashlib.sha256(captures[1][0].encode()).hexdigest(),
                "user_sha256": hashlib.sha256(captures[1][1].encode()).hexdigest(),
            }
        )

    if resolve_planner_strategy(None).identity.name != "legacy-9b78d505cb11-v1":
        raise AssertionError("Installation default changed")
    if (
        resolve_planner_strategy(SELECTOR).identity
        == resolve_planner_strategy("legacy-9b78d505cb11-v1").identity
    ):
        raise AssertionError("Versioned adapter must have a distinct identity")
    return {
        "producer_cases": len(fixture["cases"]),
        "pairs": pairs,
        "api_calls": 0,
        "scope": "pre-447 producer projection, not full historical scientific replay",
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
