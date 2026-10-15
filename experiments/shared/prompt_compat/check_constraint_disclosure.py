"""Offline historical selection and analysis identity witness, without execution."""

from __future__ import annotations

import argparse
import json
import re
import socket
from pathlib import Path
from tempfile import TemporaryDirectory

from capture import CaptureRequest, render, validate_checkout

_ROOT = Path(__file__).resolve().parent


def check_selections(selection: Path | None = None) -> list[dict]:
    from agent.prompt_rendering import bind_prompt_profile, resolve_prompt_profile
    from agent.prompt_templates.constraints import append_constraint_disclosure
    from agent.schemas.parameter_rules import (
        ParameterRules,
        resolve_parameter_rule_document,
    )
    from workflows.constraint_disclosure import workflow_constraint_context
    from workflows.run_config import WorkflowLaunchConfig

    selection = selection or _ROOT / "profiles/paper-constraint-disclosure-v1.json"
    overlay = json.loads(selection.read_text())
    rules = ParameterRules.model_validate({"train_config.epochs": {"exact": 7}})
    rows = []
    for task, selection in overlay["cases"].items():
        profile_name = selection["task_composition_overlay"]["prompt_renderer"]
        profile = resolve_prompt_profile(profile_name)
        launch = WorkflowLaunchConfig(
            **selection["workflow_launch_overlay"], workflow_parameter_rules=rules
        )
        context = workflow_constraint_context(launch, None)
        assert context is None
        with bind_prompt_profile(profile):
            assert (
                append_constraint_disclosure("Original request", context)
                == "Original request"
            )
        resolved = resolve_parameter_rule_document(
            {"train_config": {"epochs": 1}},
            workflow_rules=launch.workflow_parameter_rules,
        )
        assert resolved["train_config"]["epochs"] == 7
        rows.append({"task": task, "profile": profile_name, "status": "MATCH"})
    native = workflow_constraint_context(WorkflowLaunchConfig(), None)
    assert native is not None
    assert (
        append_constraint_disclosure("Original request", native) != "Original request"
    )
    return rows


def check_analysis_identity() -> dict:
    from agent.data_analysis.discovery import DiscoverySnapshot
    from agent.data_analysis.plan_validation import resolve_analysis_plan
    from agent.prompt_rendering import bind_prompt_profile, resolve_prompt_profile
    from agent.schemas.data_analysis.common import canonical_sha256
    from agent.schemas.data_analysis.context import DataAnalysisInput
    from agent.schemas.data_analysis.plan import AnalysisPlan
    from agent.schemas.interpretation import InterpretationOutput
    from agent.schemas.protocols.interpreter_to_data_analysis import (
        local_analysis_input,
    )
    from workflows.constraint_disclosure import workflow_constraint_context
    from workflows.run_config import WorkflowLaunchConfig

    request = CaptureRequest.model_validate_json(
        (_ROOT / "fixtures/analysis-plan.json").read_bytes()
    )
    original = DataAnalysisInput.model_validate(request.arguments["input"])
    interpretation = InterpretationOutput(
        model_types=[],
        model_descriptions={},
        total_experiments=0,
        key_findings=[],
        bottlenecks=[],
        take_home_message="Offline identity witness",
        analysis_brief=original.analysis_brief,
    )
    context = workflow_constraint_context(
        WorkflowLaunchConfig(disclose_execution_constraints=False), None
    )
    adapted = local_analysis_input(
        interpretation,
        request_id=original.request_id,
        task_context=original.task_context,
        available_assets=original.available_assets,
        declared_scope=original.declared_scope,
        access_policy=original.access_policy,
        resource_envelope=original.resource_envelope,
        allowed_skill_packs=original.allowed_skill_packs,
        storage=original.storage,
        caller=original.caller,
        prior_evidence=original.prior_evidence,
        generated_skill_registry=original.generated_skill_registry,
        human_advice=original.human_advice,
        constraint_context=context,
        allow_generated_skill_promotion=original.allow_generated_skill_promotion,
        retain_model_outputs=original.retain_model_outputs,
        recovery_policy=original.recovery_policy,
    )
    assert adapted.model_dump(mode="json") == original.model_dump(mode="json")
    assert "constraint_context" not in adapted.model_dump(mode="json")
    arguments = dict(request.arguments)
    arguments["input"] = adapted.model_dump(mode="json")
    with bind_prompt_profile(resolve_prompt_profile("paper-analysis-c0467447-v2")):
        _, user = render(request.model_copy(update={"arguments": arguments}))
    match = re.search(r"^input_digest = ([0-9a-f]{64})$", user, re.MULTILINE)
    assert match is not None
    assert match.group(1) == canonical_sha256(adapted)
    discovery = DiscoverySnapshot.model_validate(request.arguments["discovery"])
    plan = AnalysisPlan(
        plan_id="offline-identity-witness",
        input_digest=match.group(1),
        access_policy_digest=canonical_sha256(adapted.access_policy),
        discovery_snapshot_digest=discovery.snapshot_digest,
        questions=tuple(q.question_id for q in adapted.analysis_brief.questions),
        invocations=(),
        stop_policy={"max_invocations": 1},
        rationale="Validate identity only; no data or program execution.",
        non_execution_reason="Offline identity witness",
    )
    with TemporaryDirectory() as directory:
        assert (
            resolve_analysis_plan(
                plan,
                analysis_input=adapted,
                discovery=discovery,
                resolved_interfaces={},
                control_root=Path(directory),
            )
            == ()
        )
    return {
        "status": "MATCH",
        "adapter": "local_analysis_input",
        "plan_identity_accepted": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--selection", type=Path, help="Explicit historical selection overlay"
    )
    args = parser.parse_args()
    revision = validate_checkout(args.expected_revision)

    def forbidden(*args, **kwargs):
        raise AssertionError("Network access is forbidden in offline qualification")

    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden
    report = {
        "infra_revision": revision,
        "scope": "Explicit historical workflow selection and synthetic non-executing analysis plan identity; not conversation replay",
        "selection_results": check_selections(args.selection),
        "analysis_identity": check_analysis_identity(),
        "api_calls": 0,
        "training_calls": 0,
    }
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
