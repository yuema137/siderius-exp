"""Capture a declared historical rendering boundary in an isolated infra process.

This evidence tool does not replay an agent conversation. Its request explicitly
identifies the recovered inputs and the boundary being compared. Run it with the
selected infra checkout's own frozen environment, never through PYTHONPATH.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import socket
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class CaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    boundary: str
    arguments: dict[str, JsonValue]
    provenance: dict[str, JsonValue]


def render(request: CaptureRequest) -> tuple[str, str]:
    """Use a finite dispatch table; request files cannot name Python callables."""
    args = request.arguments
    if request.boundary == "interpretation.cached_synthesis":
        from cache_synthesis import render_cached_synthesis

        return render_cached_synthesis(args)
    if request.boundary in {
        "analysis.selection",
        "analysis.plan",
        "analysis.synthesis",
    }:
        from agent.data_analysis.discovery import DiscoverySnapshot
        from agent.prompt_templates import data_analysis as prompts
        from agent.schemas.data_analysis.action_identity import GeneratedProgramIdentity
        from agent.schemas.data_analysis.context import DataAnalysisInput
        from agent.schemas.data_analysis.generated_program import (
            GeneratedAnalysisProgram,
        )
        from agent.schemas.data_analysis.skills import (
            ResolvedSkillInterface,
            SkillResult,
        )
        from nodes.data_analysis_agent.data_analysis_agent import (
            DataAnalysisAgent,
            _SkillSelection,
        )
        from nodes.data_analysis_agent.report_synthesis import _ReportSynthesis

        inp = DataAnalysisInput.model_validate(args["input"])
        if request.boundary == "analysis.synthesis":
            return prompts.render_report_synthesis_prompt(
                inp,
                tuple(SkillResult.model_validate(r) for r in args["results"]),
                output_schema=_ReportSynthesis.model_json_schema(),
            )
        discovery = DiscoverySnapshot.model_validate(args["discovery"])
        if request.boundary == "analysis.selection":
            return prompts.render_skill_selection_prompt(
                inp,
                DataAnalysisAgent._candidate_cards(inp, discovery),
                output_schema=_SkillSelection.model_json_schema(),
            )
        by_id = {s.card.skill_id: s for s in discovery.skills}
        return prompts.render_analysis_plan_prompt(
            inp,
            discovery,
            tuple(by_id[k] for k in args["selected"]),
            {
                k: ResolvedSkillInterface.model_validate(v)
                for k, v in args["interfaces"].items()
            },
            generated_programs=tuple(
                (
                    GeneratedAnalysisProgram.model_validate(p),
                    GeneratedProgramIdentity.model_validate(i),
                )
                for p, i in args["programs"]
            ),
        )
    if request.boundary == "validator.system":
        from agent.schemas.model_io_contract import ModelIOContract
        from nodes.ml_code_validator_agent.ml_code_validator_agent import (
            _build_review_system_prompt,
        )

        contract = args.get("model_io_contract")
        return _build_review_system_prompt(
            None if contract is None else ModelIOContract.model_validate(contract)
        ), ""
    if request.boundary == "proposal.system":
        from agent.prompt_templates.proposal import load_stage_prompt

        return load_stage_prompt(**args), ""
    if request.boundary == "interpretation.model":
        from agent.prompt_templates.interpretation.rendering import (
            _build_per_model_prompt,
            _build_per_model_system_prompt,
        )
        from agent.schemas.hyperparam_tuning import HyperparamTuningOutput
        from agent.schemas.interpretation import InterpretationInput
        from execute_tools.evaluation_metric import MetricIdentityKey
        from execute_tools.metric_order import MetricOrder
        from nodes.result_interpretation_agent.evidence import (
            tuning_output_to_model_run_summary,
        )

        inp = InterpretationInput.model_validate(args["input"])
        order = MetricOrder(
            MetricIdentityKey(
                id=args["metric_identity"]["id"],
                direction=args["metric_identity"]["direction"],
            )
        )
        summary = tuning_output_to_model_run_summary(
            HyperparamTuningOutput.model_validate(args["tuning_output"]),
            order=order,
            required_gate_ids=frozenset(args["required_gate_ids"]),
        )
        return _build_per_model_system_prompt(inp), _build_per_model_prompt(
            summary,
            args["description"],
            structured_health_feedback=inp.enable_structured_health_feedback,
            order=order,
        )
    if request.boundary == "implementor.reasoning":
        from agent.schemas.implementor import ImplementorInput
        from nodes.ml_model_implementor.ml_model_implementor import (
            _build_reasoning_prompt,
            _build_reasoning_system_prompt,
        )

        inp = ImplementorInput.model_validate(args["input"])
        return _build_reasoning_system_prompt(inp), _build_reasoning_prompt(inp)
    if request.boundary == "implementor.code":
        from agent.schemas.implementor import ImplementorInput
        from nodes.ml_model_implementor.ml_model_implementor import (
            _build_code_prompt,
            _build_code_system_prompt,
        )

        inp = ImplementorInput.model_validate(args["input"])
        reasoning = args["reasoning"]
        if not isinstance(reasoning, str):
            raise ValueError("Code-stage capture requires an explicit reasoning string")
        return _build_code_system_prompt(inp), _build_code_prompt(reasoning, inp)
    if request.boundary == "data_analysis.generated_program.repair":
        from agent.data_analysis.generated_programs import GeneratedProgramDraft
        from agent.prompt_templates.data_analysis import (
            render_structured_output_repair_prompt,
        )

        kwargs = {
            "output_schema": GeneratedProgramDraft.model_json_schema(),
            "original_output": args["original_output"],
            "validation_errors": args["validation_errors"],
        }
        # Historical renderers predate this keyword. Adapt the invocation,
        # never the resulting text or schema.
        if (
            "stage"
            in inspect.signature(render_structured_output_repair_prompt).parameters
        ):
            kwargs["stage"] = "data_analysis.generated_program"
        return render_structured_output_repair_prompt(**kwargs)
    raise ValueError(f"Unsupported capture boundary: {request.boundary}")


def validate_checkout(expected_revision: str) -> str:
    """Bind qualification to the selected clean checkout and its own environment."""
    import agent

    checkout = Path(agent.__file__).resolve().parents[2]
    if Path(sys.prefix).resolve() != (checkout / ".venv").resolve():
        raise ValueError("Use the selected infra checkout's own frozen environment")
    revision = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != expected_revision:
        raise ValueError("Executing infra revision differs from --expected-revision")
    dirty = subprocess.check_output(
        ["git", "-C", str(checkout), "status", "--porcelain", "--", "src"], text=True
    )
    if dirty:
        raise ValueError(
            "Commit source changes before recording revision-qualified evidence"
        )

    return revision


def capture(
    request_path: Path,
    output: Path,
    expected_revision: str,
    profile_name: str | None = None,
) -> None:
    request_bytes = request_path.read_bytes()
    request = CaptureRequest.model_validate_json(request_bytes)
    revision = validate_checkout(expected_revision)

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "Network/provider access is forbidden during offline capture"
        )

    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY"):
        os.environ.pop(key, None)
    identity = None
    with ExitStack() as stack:
        if profile_name is not None:
            from agent.prompt_rendering import (
                bind_prompt_profile,
                resolve_prompt_profile,
            )

            profile = resolve_prompt_profile(profile_name)
            identity = profile.identity().model_dump(mode="json")
            stack.enter_context(bind_prompt_profile(profile))
        system, user = render(request)
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (("system", system), ("user", user)):
        (output / f"{name}.txt").write_bytes(value.encode("utf-8"))
    receipt = {
        "case_id": request.case_id,
        "boundary": request.boundary,
        "scope": "renderer comparison using explicitly supplied reconstructed inputs",
        "historical_conversation_replay": False,
        "infra_revision": revision,
        "profile": identity,
        "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
        "capture_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "capture_sources": {
            name: hashlib.sha256(
                (Path(__file__).parent / name).read_bytes()
            ).hexdigest()
            for name in (
                ["capture.py", "cache_synthesis.py"]
                if request.boundary == "interpretation.cached_synthesis"
                else ["capture.py"]
            )
        },
        "messages": {
            name: hashlib.sha256(value.encode("utf-8")).hexdigest()
            for name, value in (("system", system), ("user", user))
        },
        "api_calls": 0,
        "training_calls": 0,
        "provenance": request.provenance,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--profile")
    args = parser.parse_args()
    capture(
        args.request.resolve(),
        args.output.resolve(),
        args.expected_revision,
        args.profile,
    )
