"""Opt-in historical presentation of independently evidenced passing preflight."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from .runtime_feedback_v5 import historical_runtime_late_v5, historical_runtime_v5


def project_record(record: dict[str, Any]) -> dict[str, Any]:
    """Hide only the two additive passing-preflight fields in a rendering copy.

    A later training/scoring/Health failure does not invalidate the evidence
    that preflight passed. Static refusals have no qualified historical view;
    never reconstruct their former, possibly false, VRAM conclusions.
    """
    result = deepcopy(record)
    memory = result.get("memory")
    if memory is None:
        return result
    if not isinstance(memory, dict):
        raise TypeError("Static preflight projection requires a memory mapping")
    has_evidence = "static_preflight_evidence" in memory
    has_outcome = "preflight_outcome" in memory
    if not has_evidence and not has_outcome:
        return result
    if not has_evidence or not has_outcome:
        raise ValueError(
            "Static preflight producer must carry both evidence and outcome"
        )

    from agent.schemas.preflight import StaticPreflightEvidence

    evidence = StaticPreflightEvidence.model_validate(
        memory["static_preflight_evidence"]
    )
    if (
        memory["preflight_outcome"] != "COMPLETED_MEASUREMENT"
        or evidence.binding_caps
        or any(phase.vram_estimate_bytes is None for phase in evidence.phases)
    ):
        raise ValueError(
            "Unqualified static preflight refusal or incomplete passing evidence; "
            "historical v6 projects only an evidenced passing preflight"
        )
    memory.pop("static_preflight_evidence")
    memory.pop("preflight_outcome")
    return result


def _provider(*, late: bool):
    from core.planner_strategy_identity import (
        PlannerStrategyIdentity,
        source_fingerprint,
    )

    original = historical_runtime_late_v5() if late else historical_runtime_v5()
    name = "legacy-9b78d505cb11-paper" + ("-late" if late else "") + "-preflight-v6"

    def render(*, memory_history, **arguments):
        return original.user_renderer(
            memory_history=[project_record(record) for record in memory_history],
            **arguments,
        )

    return replace(
        original,
        identity=PlannerStrategyIdentity(
            name=name,
            version="6",
            content_sha256=source_fingerprint(
                {
                    "v5_identity.json": original.identity.model_dump_json().encode(),
                    "static_preflight_v6.py": Path(__file__).read_bytes(),
                }
            ),
        ),
        user_renderer=render,
    )


def historical_preflight_v6():
    return _provider(late=False)


def historical_preflight_late_v6():
    return _provider(late=True)
