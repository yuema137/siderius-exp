"""Synthetic passing preflight through the actual final planner boundary.

Run with the candidate infra's own Python and this package installed normally.
The exp checkout's published infra pin predates the new evidence schema.
"""

import json
from copy import deepcopy
from importlib.resources import files

import pytest
from siderius_planner_compat.self_check import _CaptureBridge
from siderius_planner_compat.static_preflight_v6 import project_record

pytest.importorskip("agent.schemas.preflight")


def passing_record(status="success"):
    return {
        "exp_id": "synthetic_preflight_001",
        "model_type": "synthetic",
        "status": status,
        "timestamp": "2026-10-07T00:00:00Z",
        "params": {},
        "is_trial": True,
        "attempt_role": "trial",
        "denoising_score": 0.5 if status == "success" else None,
        "memory": {
            "hypothesis": "Controlled preflight evidence",
            "conclusion": "Preserved downstream result",
            "discovery": "Preserved discovery",
            "memory_update": "Preserved next-step advice",
            "expert_advice_followed": "No external advice supplied",
            "vram_estimate_gb": 0.75,
            "vram_budget_gb": 1.0,
            "preflight_outcome": "COMPLETED_MEASUREMENT",
            "static_preflight_evidence": {
                "version": "static-preflight-v1",
                "phases": [
                    {
                        "phase": "training",
                        "batch_size": 2,
                        "vram_cap_bytes": 1073741824,
                        "vram_estimate_bytes": 805306368,
                        "estimator": "training_saved_tensors_v1",
                        "intensity_product": 16,
                        "intensity_limit": 32,
                    },
                    {
                        "phase": "inference",
                        "batch_size": 4,
                        "vram_cap_bytes": 1073741824,
                        "vram_estimate_bytes": 536870912,
                        "estimator": "inference_leaf_sum_v1",
                    },
                ],
            },
        },
    }


def planner_arguments():
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
@pytest.mark.parametrize(
    "status", ["success", "failed_mode_collapse", "error_training"]
)
def test_same_final_messages_without_changing_stored_facts(late, status):
    current = passing_record(status)
    before = deepcopy(current)
    historical = deepcopy(current)
    historical["memory"].pop("static_preflight_evidence")
    historical["memory"].pop("preflight_outcome")
    prefix = "legacy-9b78d505cb11-paper" + ("-late" if late else "")
    captured = []
    for version, record in [("runtime-v5", historical), ("preflight-v6", current)]:
        bridge = _CaptureBridge()
        bridge.plan(
            **(
                planner_arguments()
                | {
                    "planner_strategy": f"{prefix}-{version}",
                    "memory_history": [record],
                }
            )
        )
        assert len(bridge.captures) == 1
        captured.append(bridge.captures[0])
    assert captured[0] == captured[1]
    unprojected = _CaptureBridge()
    unprojected.plan(
        **(
            planner_arguments()
            | {"planner_strategy": f"{prefix}-runtime-v5", "memory_history": [current]}
        )
    )
    assert unprojected.captures[0] != captured[0]
    assert project_record(current) == historical
    assert current == before
    assert project_record(historical) == historical


@pytest.mark.parametrize(
    "defect",
    [
        "missing_evidence",
        "missing_outcome",
        "version",
        "outcome",
        "vram",
        "intensity",
        "unobserved_vram",
        "static_refusal",
        "null_evidence",
        "null_outcome",
    ],
)
def test_refuses_unqualified_producers_before_any_provider_request(defect):
    current = passing_record()
    memory = current["memory"]
    phase = memory["static_preflight_evidence"]["phases"][0]
    if defect == "missing_evidence":
        memory.pop("static_preflight_evidence")
    elif defect == "missing_outcome":
        memory.pop("preflight_outcome")
    elif defect == "version":
        memory["static_preflight_evidence"]["version"] = "future-v2"
    elif defect == "outcome":
        memory["preflight_outcome"] = "UNKNOWN"
    elif defect == "vram":
        phase["vram_estimate_bytes"] = phase["vram_cap_bytes"] + 1
    elif defect == "intensity":
        phase["intensity_product"] = phase["intensity_limit"] + 1
    elif defect == "unobserved_vram":
        phase["vram_estimate_bytes"] = None
        phase["estimator"] = None
    elif defect == "static_refusal":
        memory["preflight_outcome"] = "STATIC_PREFLIGHT_REFUSAL"
        phase["intensity_product"] = phase["intensity_limit"] + 1
        current["status"] = "skipped_resource_admission"
    else:
        memory[
            {
                "null_evidence": "static_preflight_evidence",
                "null_outcome": "preflight_outcome",
            }[defect]
        ] = None
    before = deepcopy(current)
    bridge = _CaptureBridge()
    with pytest.raises(ValueError):
        bridge.plan(
            **(
                planner_arguments()
                | {
                    "planner_strategy": "legacy-9b78d505cb11-paper-preflight-v6",
                    "memory_history": [current],
                }
            )
        )
    assert not bridge.captures
    assert current == before


def test_old_history_without_static_fields_is_preserved():
    for record in [{}, {"memory": None}, {"memory": {"conclusion": "Old refusal"}}]:
        assert project_record(record) == record


@pytest.mark.parametrize("late", [False, True])
def test_passing_preflight_composes_with_later_runtime_refusal(late):
    from agent.skills.evaluate_vram_skill.evidence import preflight_memory_fields

    fixture = json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/runtime_feedback_producer.json")
        .read_text()
    )
    historical = fixture["record"]
    current = deepcopy(historical)
    # Use the same validated evidence transport used by the recorder. The
    # later time refusal and its version marker must survive the v6 layer
    # so the inherited v5 layer can apply its separately qualified view.
    current["memory"].update(preflight_memory_fields(passing_record()["memory"]))
    before = deepcopy(current)
    prefix = "legacy-9b78d505cb11-paper" + ("-late" if late else "")
    captures = []
    for version, record in [("runtime-v5", historical), ("preflight-v6", current)]:
        bridge = _CaptureBridge()
        bridge.plan(
            **(
                planner_arguments()
                | {
                    "planner_strategy": f"{prefix}-{version}",
                    "memory_history": [record],
                }
            )
        )
        captures.append(bridge.captures)
    assert len(captures[0]) == 1
    assert captures[0] == captures[1]
    assert project_record(current) == historical
    assert current == before
