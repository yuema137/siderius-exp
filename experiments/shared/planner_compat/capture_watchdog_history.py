"""Capture full planner requests with synthetic watchdog history and paper inputs.

Execute separately in each selected framework checkout's own environment.
Reference requests use the old watchdog shape; the candidate uses its explicit
v10 profile and deadline metadata. No historical conversation replay is claimed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from pydantic import ConfigDict


def capture(case: str, model: Path, revision: str, output: Path, profile: str | None):
    with tempfile.TemporaryDirectory(prefix="paper-watchdog-capture-") as temporary:
        root = Path(temporary)
        environment = {
            "SIDERIUS_GENERATED_LIBRARY_DIR": str(root / "generated_library"),
            "SIDERIUS_CALIBRATION_DIR": str(root / "calibration"),
            "SIDERIUS_PLUGIN_DIRS": str(root / "plugins"),
            "SIDERIUS_CHAIN_WORKSPACE": str(root / "workspace"),
        }
        for directory in environment.values():
            Path(directory).mkdir()
        with patch.dict(os.environ, environment):
            _capture(case, model, revision, output, profile)


def _capture(case: str, model: Path, revision: str, output: Path, profile: str | None):
    import agent

    checkout = Path(agent.__file__).resolve().parents[2]
    if Path(sys.prefix).resolve() != (checkout / ".venv").resolve():
        raise ValueError("Use the selected framework checkout's own frozen environment")
    actual = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(checkout), "diff", "HEAD", "--", "src"], text=True
    )
    if actual != revision or dirty:
        raise ValueError("Framework revision mismatch or modified source")

    def forbidden(*args, **kwargs):
        raise AssertionError("Network, providers, training and scoring are forbidden")

    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

    from agent.llm_bridge import LLMBridge
    from agent.prompt_templates.tuner.rendering import TunerTaskRender
    from agent.schemas.custom_loss_contract import CustomLossInventory
    from agent.skills.check_config_format_skill.wrapper import run_skill
    from execute_tools.evaluation_metric import MetricSpec, ScoreabilityContract
    from ml_models.plugin_loader import register_model_in_memory

    class Scoreability(ScoreabilityContract):
        model_config = ConfigDict(extra="allow")

        def check(self, deliverables):
            return forbidden()

    class Capture(LLMBridge):
        def __init__(self):
            self.messages = []

        def generate(self, system_prompt, user_prompt, **kwargs):
            self.messages.append({"system": system_prompt, "user": user_prompt})
            return {}

    fixture = (
        Path(__file__).parent
        / "src/siderius_planner_compat/fixtures/paper_task_startups.json"
    )
    fixture_bytes = fixture.read_bytes()
    data = json.loads(fixture_bytes)["cases"][case]
    if hashlib.sha256(model.read_bytes()).hexdigest() != data["model_source_sha256"]:
        raise ValueError("Archived model source mismatch")
    if register_model_in_memory(str(model)) != data["model_type"]:
        raise ValueError("Registered model identity mismatch")
    appendix_fixture = fixture.with_name("paper_ligo_boundary.json")
    appendix_bytes = appendix_fixture.read_bytes()
    appendix = json.loads(appendix_bytes)
    arguments = deepcopy(data["arguments"])
    arguments["task_render"] = TunerTaskRender.model_validate(arguments["task_render"])
    arguments["custom_loss_inventory"] = CustomLossInventory.model_validate(
        arguments["custom_loss_inventory"]
    )
    metric = arguments["metric_spec"]
    arguments["metric_spec"] = MetricSpec.model_validate(
        metric | {"scoreability": Scoreability(**metric["scoreability"])}
    )
    manual = run_skill(None)
    if manual["status"] != "success":
        raise ValueError("Production configuration manual failed")
    arguments["config_manual"] = manual["data"]
    if profile:
        from agent.schemas.planner_timing import PlannerTimingContext

        arguments["planner_strategy"] = profile
        arguments["timing_context"] = PlannerTimingContext.model_validate(
            arguments["timing_context"]
        )
    else:
        if actual != data["reference_infra_revision"]:
            raise ValueError("Reference does not match the task's archived revision")
        arguments.pop("planner_strategy")
        context = arguments.pop("timing_context")
        if context["formal_training_scope_source"] == "agent":
            if (
                context["formal_eval_portion"]
                != appendix["timing_context"]["formal_eval_portion"]
            ):
                raise ValueError("Historical Formal appendix does not cover this scope")
            # The original planning producer added this before LLMBridge.plan.
            # The modern historical profile owns that same frozen appendix.
            arguments["task_description"] += appendix["historical_formal_appendix"]

    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for witness, enabled, mode in (
        ("disabled_native", False, "budget-ceiling-v1"),
        ("disabled_legacy", False, "forecast-tightening-v1"),
        ("enabled_legacy", True, "forecast-tightening-v1"),
    ):
        watchdog = {
            "enabled": enabled,
            "grace_seconds": 10.0,
            "poll_seconds": 1.0,
            "floor_seconds": 60.0,
            "safety_factor": None,
            "max_phase_seconds": None,
        }
        if profile:
            watchdog["deadline_policy"] = mode
        history = [
            {
                "status": "skipped_time_risk",
                "runtime_verification": {
                    "runtime_policy": {
                        "operator_budget_seconds": arguments[
                            "trial_time_budget_minutes"
                        ]
                        * 60.0,
                        "watchdog": watchdog,
                    }
                },
            }
        ]
        before = deepcopy(history)
        bridge = Capture()
        bridge.plan(**(arguments | {"memory_history": history}))
        assert len(bridge.messages) == 1 and history == before
        messages = bridge.messages[0]
        for label, text in messages.items():
            (output / f"{witness}-{label}.txt").write_text(text)
        rows.append(
            {
                "witness": witness,
                "messages": {
                    label: hashlib.sha256(text.encode()).hexdigest()
                    for label, text in messages.items()
                },
            }
        )
    receipt = {
        "case": case,
        "infra_revision": actual,
        "profile": profile,
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "appendix_fixture_sha256": hashlib.sha256(appendix_bytes).hexdigest(),
        "capture_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "requests": rows,
        "api_calls": 0,
        "training_calls": 0,
        "scope": "Full planner requests: archived task inputs plus synthetic watchdog history; not recovered historical conversations",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", required=True, choices=("tess", "ligo", "project8", "tidmad")
    )
    parser.add_argument("--model-plugin", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile")
    args = parser.parse_args()
    capture(args.case, args.model_plugin, args.revision, args.output, args.profile)
