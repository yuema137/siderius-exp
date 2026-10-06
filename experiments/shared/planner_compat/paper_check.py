"""Compare final planner text offline using frozen LIGO-derived branch inputs.

Run with each selected infra checkout's own frozen Python environment. The
historical model plugin is an explicit, hash-checked input; no data or API key
is needed. This checks shared prompt assembly, not scientific execution replay.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def check(
    fixture,
    model_plugin: Path,
    *,
    reference: bool,
    manual: str,
    planner_strategy: str = "legacy-9b78d505cb11-v1",
):
    if (
        hashlib.sha256(model_plugin.read_bytes()).hexdigest()
        != fixture["model_source_sha256"]
    ):
        raise ValueError(
            "Historical model plugin does not match the frozen source digest"
        )

    def forbidden(*args, **kwargs):
        raise AssertionError("No network or scoring is permitted in this offline check")

    # This command is a dedicated offline process. Do not inherit ambient model
    # registries, scientific workspaces or provider credentials.
    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY"):
        os.environ.pop(name, None)

    from agent import llm_bridge
    from agent.llm_bridge import LLMBridge
    from agent.prompt_templates.tuner.rendering import TunerTaskRender
    from agent.schemas.custom_loss_contract import CustomLossInventory
    from execute_tools.evaluation_metric import MetricSpec, ScoreabilityContract
    from ml_models.plugin_loader import register_model_in_memory

    checkout = Path(llm_bridge.__file__).resolve().parents[2]
    if Path(sys.prefix).resolve() != (checkout / ".venv").resolve():
        raise ValueError("Use the selected infra checkout's own frozen virtualenv")
    revision = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if reference:
        expected_revision = fixture[
            "reference_revision" if manual == "historical" else "pre_pr_revision"
        ]
        if revision != expected_revision:
            raise ValueError(
                "Reference checkout revision does not match the frozen oracle"
            )

    class UnexecutedScoreability(ScoreabilityContract):
        """Preserve serialized metric identity; refuse any actual scoring."""

        def check(self, deliverables):
            return forbidden()

    class NoClient:
        def __getattr__(self, name):
            return forbidden()

    class Capture(LLMBridge):
        def __init__(self):
            super().__init__(
                provider="openai", model_id="offline", api_key="offline-no-key"
            )
            self.client = NoClient()
            self.reflect_client = NoClient()
            self.messages = []

        def _chat_json(self, client, model_name, system_prompt, user_prompt, **kwargs):
            self.messages.append((system_prompt, user_prompt))
            return {}

    if (
        register_model_in_memory(str(model_plugin))
        != fixture["base_arguments"]["force_model"]
    ):
        raise AssertionError("Unexpected registered model identity")
    results = []
    for case in fixture["cases"]:
        args = copy.deepcopy(fixture["base_arguments"] | case["arguments"])
        args["config_manual"] = fixture["config_manuals"][manual]
        task = fixture["task_description"]
        if case["training_validation_portion"] is not None:
            task += fixture["validation_disclosure"]
        if reference and case["formal_training_scope_source"] == "agent":
            task += fixture["historical_formal_appendix"]
        args["task_description"] = task
        args["task_render"]["loss_context"]["output_has_temporal_axis"] = case[
            "output_has_temporal_axis"
        ]
        args["task_render"] = TunerTaskRender.model_validate(args["task_render"])
        metric = args["metric_spec"]
        args["metric_spec"] = MetricSpec.model_validate(
            metric | {"scoreability": UnexecutedScoreability(**metric["scoreability"])}
        )
        args["custom_loss_inventory"] = CustomLossInventory.model_validate(
            args["custom_loss_inventory"]
        )
        if not reference:
            from agent.schemas.planner_timing import PlannerTimingContext

            # This provider uses only the Formal appendix fields. The complete
            # first-call context is retained as capture evidence; these are
            # branch fixtures, not simulated execution decisions for later rounds.
            context = copy.deepcopy(fixture["timing_context"])
            for field in (
                "formal_training_scope_source",
                "training_validation_portion",
            ):
                context[field] = case[field]
            args["timing_context"] = PlannerTimingContext.model_validate(context)
            args["planner_strategy"] = planner_strategy
        bridge = Capture()
        bridge.plan(**args)
        if len(bridge.messages) != 1:
            raise AssertionError("Expected exactly one final system/user pair")
        system, user = bridge.messages[0]
        row = {
            "id": case["id"],
            "system_sha256": digest(system),
            "user_sha256": digest(user),
        }
        expected = case["expected"][manual]
        if row != expected:
            raise AssertionError(f"Final prompt bytes changed: {case['id']} ({manual})")
        results.append(row)
    return {
        "manual": manual,
        "reference": reference,
        "infra_revision": revision,
        "planner_strategy": None if reference else planner_strategy,
        "pairs": results,
        "api_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-plugin", required=True, type=Path)
    parser.add_argument("--reference", action="store_true")
    parser.add_argument("--manual", choices=("historical", "pre_pr"), required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--planner-strategy", default="legacy-9b78d505cb11-v1")
    args = parser.parse_args()
    fixture_path = (
        Path(__file__).parent
        / "src/siderius_planner_compat/fixtures/paper_ligo_boundary.json"
    )
    fixture = json.loads(fixture_path.read_text())
    with tempfile.TemporaryDirectory(prefix="siderius-paper-prompt-") as directory:
        for name in (
            "SIDERIUS_PLUGIN_DIRS",
            "SIDERIUS_GENERATED_LIBRARY_DIR",
            "SIDERIUS_CHAIN_WORKSPACE",
            "SIDERIUS_CALIBRATION_DIR",
        ):
            os.environ[name] = directory
        result = check(
            fixture,
            args.model_plugin.resolve(),
            reference=args.reference,
            manual=args.manual,
            planner_strategy=args.planner_strategy,
        )
    with args.output.open("x") as output:
        output.write(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
