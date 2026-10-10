"""Capture complete reflector requests with declared synthetic provenance witnesses.

Run with the selected framework checkout's own environment. Reference captures
use plan-only events; current captures retain both corrected events and the old
checkpoint, selected only by an explicit qualified paper prompt profile.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path

from pydantic import ConfigDict


def capture(case: str, output: Path, revision: str, profile_name: str | None) -> None:
    import agent

    checkout = Path(agent.__file__).resolve().parents[2]
    if Path(sys.prefix).resolve() != (checkout / ".venv").resolve():
        raise ValueError("Use the selected framework checkout's own environment")
    actual = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(checkout), "diff", "HEAD", "--", "src"], text=True
    )
    if actual != revision or dirty:
        raise ValueError("Framework revision mismatch or modified source")

    def forbidden(*args, **kwargs):
        raise AssertionError("Network, provider and scoring access are forbidden")

    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

    from agent.llm_bridge import LLMBridge
    from agent.prompt_templates.tuner.rendering import TunerTaskRender
    from agent.schemas.execution_provenance import ExecutionProvenance, ResolutionEvent
    from execute_tools.evaluation_metric import MetricSpec, ScoreabilityContract

    class Scoreability(ScoreabilityContract):
        model_config = ConfigDict(extra="allow")

        def check(self, deliverables):
            return forbidden()

    class Capture(LLMBridge):
        def __init__(self):
            # No provider clients or credentials are constructed for a text capture.
            self.reflect_client = object()
            self.reflect_model_name = "offline-reflector-capture"
            self.reflect_provider = "openai"
            self.messages = []

        def _chat_json(self, client, model, system_prompt, user_prompt, **kwargs):
            self.messages.append({"system": system_prompt, "user": user_prompt})
            return {}

    fixture = (
        Path(__file__).parent.parent
        / "planner_compat/src/siderius_planner_compat/fixtures/paper_task_startups.json"
    )
    arguments = json.loads(fixture.read_text())["cases"][case]["arguments"]
    metric = arguments["metric_spec"]
    metric_spec = MetricSpec.model_validate(
        metric | {"scoreability": Scoreability(**metric["scoreability"])}
    )
    task_render = TunerTaskRender.model_validate(arguments["task_render"])
    old = ResolutionEvent(
        field_path="trial_strategy",
        proposed="'anchors'",
        executed="'snapshot'",
        authority="partial_scope_strategy_normalization",
    )
    corrected = ResolutionEvent(
        field_path="eval_portion",
        proposed="1.0",
        executed="0.25",
        authority="resolved_round_workload",
    )
    witnesses = {
        "none": None,
        "unchanged": ((), ()),
        "restored_authored": ((), (old,)),
        "new_execution_disagreement": ((corrected,), ()),
        "different_disagreements": ((corrected,), (old,)),
    }
    binding = nullcontext()
    if profile_name:
        from agent.prompt_rendering import bind_prompt_profile, resolve_prompt_profile

        binding = bind_prompt_profile(resolve_prompt_profile(profile_name))
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    with binding:
        for name, pair in witnesses.items():
            provenance = None
            if pair is not None:
                execution, checkpoint = pair
                provenance = (
                    ExecutionProvenance(
                        events=execution, plan_resolution_events=checkpoint
                    )
                    if profile_name
                    else ExecutionProvenance(events=checkpoint)
                )
            before = None if provenance is None else provenance.model_dump()
            bridge = Capture()
            bridge.reflect(
                exp_id="offline-reflector-witness",
                hypothesis="The authored parameters improve the declared metric.",
                actual_results={"denoising_score": 0.5, "final_loss": 0.25},
                metric_spec=metric_spec,
                task_render=task_render,
                execution_provenance=provenance,
            )
            assert len(bridge.messages) == 1
            assert provenance is None or provenance.model_dump() == before
            messages = bridge.messages[0]
            for label, text in messages.items():
                (output / f"{name}-{label}.txt").write_text(text)
            rows.append(
                {
                    "witness": name,
                    "messages": {
                        label: hashlib.sha256(text.encode()).hexdigest()
                        for label, text in messages.items()
                    },
                }
            )
    receipt = {
        "case": case,
        "infra_revision": actual,
        "profile": profile_name,
        "input_fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "capture_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "requests": rows,
        "api_calls": 0,
        "training_calls": 0,
        "scope": "Complete reflector requests with synthetic provenance and archived task/metric inputs; not recovered historical conversations",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", required=True, choices=("tess", "ligo", "project8", "tidmad")
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--profile")
    args = parser.parse_args()
    capture(args.case, args.output, args.expected_revision, args.profile)
