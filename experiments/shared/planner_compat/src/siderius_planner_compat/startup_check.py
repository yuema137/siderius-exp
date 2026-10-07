"""Recheck four actual task startup captures with current production manual assembly.

Each invocation uses one archived model, supplied explicitly and hash checked.
No dataset is required: the fixture preserves the actual startup arguments,
while expected message hashes come from each task's original infra revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
from importlib.resources import files
from pathlib import Path

from pydantic import ConfigDict


def check(
    case_name: str, model_plugin: Path, *, planner_strategy: str | None = None
) -> dict:
    def forbidden(*args, **kwargs):
        raise AssertionError(
            "No network or scoring is permitted in offline startup checks"
        )

    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    from agent.prompt_templates.tuner.rendering import TunerTaskRender
    from agent.schemas.custom_loss_contract import CustomLossInventory
    from agent.schemas.planner_timing import PlannerTimingContext
    from agent.skills.check_config_format_skill.wrapper import run_skill
    from execute_tools.evaluation_metric import MetricSpec, ScoreabilityContract
    from ml_models.plugin_loader import register_model_in_memory

    from .self_check import _CaptureBridge

    class UnexecutedScoreability(ScoreabilityContract):
        # Task plugins extend the serialized identity. Preserve their fields
        # without importing a scorer or claiming to validate its execution.
        model_config = ConfigDict(extra="allow")

        def check(self, deliverables):
            return forbidden()

    fixture_bytes = (
        files("siderius_planner_compat")
        .joinpath("fixtures/paper_task_startups.json")
        .read_bytes()
    )
    case = json.loads(fixture_bytes)["cases"][case_name]
    if (
        hashlib.sha256(model_plugin.read_bytes()).hexdigest()
        != case["model_source_sha256"]
    ):
        raise ValueError("Model source does not match the archived startup")
    if register_model_in_memory(str(model_plugin)) != case["model_type"]:
        raise ValueError("Model registered under an unexpected identity")
    arguments = case["arguments"]
    if planner_strategy is not None:
        arguments["planner_strategy"] = planner_strategy
    arguments["task_render"] = TunerTaskRender.model_validate(arguments["task_render"])
    arguments["timing_context"] = PlannerTimingContext.model_validate(
        arguments["timing_context"]
    )
    arguments["custom_loss_inventory"] = CustomLossInventory.model_validate(
        arguments["custom_loss_inventory"]
    )
    metric = arguments["metric_spec"]
    arguments["metric_spec"] = MetricSpec.model_validate(
        metric | {"scoreability": UnexecutedScoreability(**metric["scoreability"])}
    )
    manual = run_skill(None)
    if manual["status"] != "success":
        raise ValueError("Current configuration manual could not be assembled")
    arguments["config_manual"] = manual["data"]
    bridge = _CaptureBridge()
    bridge.plan(**arguments)
    if len(bridge.captures) != 1:
        raise AssertionError("Expected one final message pair")
    actual = {
        name: hashlib.sha256(text.encode()).hexdigest()
        for name, text in zip(("system", "user"), bridge.captures[0], strict=True)
    }
    if actual != case["expected"]:
        raise AssertionError(f"Historical startup prompt changed: {case_name}")
    return {
        "case": case_name,
        "planner_strategy": arguments["planner_strategy"],
        "reference_infra_revision": case["reference_infra_revision"],
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "message_sha256": actual,
        "api_calls": 0,
        "training_calls": 0,
        "scope": case["scope"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", required=True, choices=("tess", "ligo", "project8", "tidmad")
    )
    parser.add_argument("--model-plugin", required=True, type=Path)
    parser.add_argument(
        "--planner-strategy",
        help="Explicit provider to compare with the historical messages",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            check(
                args.case,
                args.model_plugin.resolve(),
                planner_strategy=args.planner_strategy,
            ),
            indent=2,
        )
    )
