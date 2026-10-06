"""Capture actual tuner startup inputs and final messages without LLM or training.

Run in an isolated process using the selected infra checkout's own environment.
The explicit input JSON supplies composition, dataset, archived seed plugin,
their expected identities, and tuner parameters. Outputs go to a new directory.
This captures startup only; it never invents responses for later workflow nodes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
from pathlib import Path


def capture(spec_path: Path, output: Path) -> None:
    spec = json.loads(spec_path.read_text())
    output.mkdir(parents=True, exist_ok=False)
    model = Path(spec["seed_plugin_path"])
    if hashlib.sha256(model.read_bytes()).hexdigest() != spec["seed_plugin_sha256"]:
        raise ValueError("Archived model source digest mismatch")
    description = Path(spec["model_description_path"])
    if hashlib.sha256(description.read_bytes()).hexdigest() != spec["model_description_sha256"]:
        raise ValueError("Archived model description digest mismatch")
    description_target = (
        output / "plugins" / "archive" / spec["tuner_parameters"]["model_type"] / "description.md"
    )
    description_target.parent.mkdir(parents=True)
    description_target.write_bytes(description.read_bytes())

    def forbidden(*args, **kwargs):
        raise AssertionError("Provider/network/training access forbidden in startup capture")

    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY"):
        os.environ.pop(key, None)
    # Historical constructors require a key even when provider access is blocked.
    os.environ["OPENAI_API_KEY"] = "offline-capture-not-a-credential"
    for name, suffix in (
        ("SIDERIUS_GENERATED_LIBRARY_DIR", "generated_library"),
        ("SIDERIUS_CALIBRATION_DIR", "calibration"),
        ("SIDERIUS_PLUGIN_DIRS", "plugins"),
    ):
        os.environ[name] = str(output / suffix)
    os.environ["SIDERIUS_CHAIN_WORKSPACE"] = str(output)

    from agent import llm_bridge
    from agent.llm_bridge import LLMBridge
    from agent.schemas.hyperparam_tuning import HyperparamTuningInput
    from ml_models.plugin_loader import register_model_in_memory
    from nodes.ml_hyperparameter_tune_agent import HyperparamTuningAgent
    from workflows.task_composition import (
        bind_run_task_composition,
        build_task_composition_ref,
        compose_run_task_bindings,
    )

    checkout = Path(llm_bridge.__file__).resolve().parents[2]
    if Path(sys.prefix).resolve() != (checkout / ".venv").resolve():
        raise ValueError("Use the executing infra checkout's own frozen environment")

    def encode(value):
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        raise TypeError(type(value).__name__)

    class Captured(BaseException):
        """Stop before planner responses can reach execution."""

    class Capture(LLMBridge):
        def plan(self, memory_history, **kwargs):
            (output / "planner_arguments.json").write_text(
                json.dumps({"memory_history": memory_history, **kwargs}, default=encode, indent=2)
                + "\n"
            )
            return super().plan(memory_history, **kwargs)

        def generate(self, system_prompt, user_prompt, **kwargs):
            (output / "messages.json").write_text(
                json.dumps({"system": system_prompt, "user": user_prompt}, indent=2) + "\n"
            )
            raise Captured()

    LLMBridge._create_completion = staticmethod(forbidden)
    # In the full workflow the implementor has already registered this model.
    # Older standalone tuner revisions only copied its source for subprocesses.
    if register_model_in_memory(str(model)) != spec["tuner_parameters"]["model_type"]:
        raise ValueError("Archived model could not be registered under its declared identity")
    composition = compose_run_task_bindings(spec["composition"])
    if composition.semantic_fingerprint != spec["composition_fingerprint"]:
        raise ValueError("Task composition identity mismatch")
    inputs = HyperparamTuningInput(
        **spec["tuner_parameters"],
        seed_plugin_path=str(model),
        task_description=composition.task_description,
        task_composition_ref=build_task_composition_ref(composition),
        data_dir=spec["data_dir"],
        llm_provider="openai",
        llm_model_id="offline-capture",
        storage={"backend": "local", "local": {"workspace": str(output), "run_name": "capture"}},
    )
    (output / "tuner_input.json").write_text(inputs.model_dump_json(indent=2) + "\n")
    try:
        with bind_run_task_composition(composition, physical_data_root=inputs.data_dir):
            HyperparamTuningAgent(bridge_factory=Capture).run(inputs)
    except Captured:
        receipt = {
            "infra_revision": subprocess.check_output(
                ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
            ).strip(),
            "input_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
            "api_calls": 0,
            "training_calls": 0,
            "scope": "production tuner startup and first planner message only",
        }
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    else:
        raise AssertionError("Planner capture boundary was not reached")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    capture(args.input.resolve(), args.output.resolve())
