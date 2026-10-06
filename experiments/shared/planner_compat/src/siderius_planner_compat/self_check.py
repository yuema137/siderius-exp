"""Offline checks for the installed compatibility package at the bridge boundary.

Run with the qualified infra environment: python -m siderius_planner_compat.self_check.
No API credentials, real client access, task datasets or GPU work are permitted.
"""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files

from agent.llm_bridge import LLMBridge
from agent.prompt_templates.tuner.rendering import TunerTaskRender
from agent.schemas.custom_loss_contract import CustomLossInventory
from agent.schemas.planner_timing import PlannerTimingContext
from execute_tools.evaluation_metric import MetricSpec, PresenceScoreabilityContract


class _NoNetwork:
    def __getattr__(self, name):
        raise AssertionError(f"Offline compatibility check attempted client access: {name}")


class _CaptureBridge(LLMBridge):
    def __init__(self):
        super().__init__(provider="openai", model_id="offline-fixture", api_key="offline-no-key")
        self.client = _NoNetwork()
        self.reflect_client = _NoNetwork()
        self.captures = []

    def _chat_json(self, client, model_name, system_prompt, user_prompt, **kwargs):
        self.captures.append((system_prompt, user_prompt))
        return {}


def _assert_pair(case, bridge):
    if len(bridge.captures) != 1:
        raise AssertionError(f"{case['id']}: expected exactly one provider boundary capture")
    for label, text in zip(("system", "user"), bridge.captures[0], strict=True):
        if hashlib.sha256(text.encode()).hexdigest() != case[f"expected_{label}_sha256"]:
            raise AssertionError(f"{case['id']}: historical {label} prompt bytes changed")


def check() -> dict[str, object]:
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
    for case in reference["cases"]:
        bridge = _CaptureBridge()
        bridge.plan(
            **(
                base
                | case["arguments"]
                | {
                    "planner_strategy": "legacy-9b78d505cb11-v1",
                    "timing_context": PlannerTimingContext.model_validate(case["timing_context"]),
                }
            )
        )
        _assert_pair(case, bridge)

    early = json.loads(
        files("siderius_planner_compat").joinpath("fixtures/early_legacy_boundary.json").read_text()
    )
    if early["base_fixture"] != "current_legacy_boundary.json":
        raise AssertionError("Early comparison references an unexpected input fixture")
    for case in early["cases"]:
        bridge = _CaptureBridge()
        bridge.plan(**(base | case["arguments"] | {"planner_strategy": "legacy-691617f04b42-v1"}))
        _assert_pair(case, bridge)

    loss = json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/loss_strategy_boundary.json")
        .read_text()
    )
    if loss["base_fixture"] != "current_legacy_boundary.json":
        raise AssertionError("Loss comparison references an unexpected input fixture")
    for case in loss["cases"]:
        bridge = _CaptureBridge()
        task_render = TunerTaskRender.model_validate(
            reference["task_render"] | {"loss_context": case["loss_context"]}
        )
        bridge.plan(
            **(
                base
                | case["arguments"]
                | {
                    "planner_strategy": "legacy-9b78d505cb11-v1",
                    "task_render": task_render,
                }
            )
        )
        _assert_pair(case, bridge)

    for inventory in (None, CustomLossInventory(composed=True)):
        bridge = _CaptureBridge()
        bridge.plan(
            **(
                base
                | {
                    "planner_strategy": "legacy-691617f04b42-v1",
                    "custom_loss_inventory": inventory,
                }
            )
        )
        if len(bridge.captures) != 1:
            raise AssertionError("Early empty-registry adapter did not reach the provider boundary")
    bridge = _CaptureBridge()
    try:
        bridge.plan(
            **(
                base
                | {
                    "planner_strategy": "legacy-691617f04b42-v1",
                    "custom_loss_inventory": CustomLossInventory(
                        composed=True, unavailable_reason="unverified registry"
                    ),
                }
            )
        )
    except ValueError as exc:
        if "verified historical custom-loss registry" not in str(exc):
            raise
    else:
        raise AssertionError("Early adapter silently discarded uncertain registry information")
    if bridge.captures:
        raise AssertionError("Early adapter called a provider before refusing uncertain registry")
    return {
        "current_legacy_prompt_pairs": len(reference["cases"]),
        "early_legacy_prompt_pairs": len(early["cases"]),
        "composed_loss_prompt_pairs": len(loss["cases"]),
        "early_empty_registry_boundary_cases": 2,
        "early_uncertain_registry_refusal": True,
        "reference_infra_revision": reference["reference_infra_revision"],
        "historical_scientific_replay": "not established",
        "api_calls": 0,
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
