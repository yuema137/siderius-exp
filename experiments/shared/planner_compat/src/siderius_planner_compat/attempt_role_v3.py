"""Opt-in historical planner input representation; current records stay correct."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from .ordering_v2 import historical_ordering_v2
from .ordering_v2 import project_record as project_ordering

SELECTOR = "legacy-9b78d505cb11-attempt-role-v3"

# Frozen raw producer shapes at infra 12007857, not execution policy.
_UNSTAMPED = frozenset(
    {
        "skipped_oom_risk",
        "skipped_time_risk",
        "skipped_schema_violation",
        "skipped_resource_admission",
        "skipped_infrastructure_failure",
        "error_training",
        "error_training_oom",
        "error_inference",
        "error_inference_oom",
        "error_scoring",
    }
)


def project_record(record: dict[str, Any]) -> dict[str, Any]:
    """Restore pre-369 raw role representation, then pre-447 ordering.

    Only explicit current provenance triggers conversion. Historical inputs
    pass through unchanged. Unknown producer shapes fail rather than guessing.
    This projection is for raw recorder history, not normalized model dumps.
    """
    role = record.get("attempt_role")
    if role is None:
        return project_ordering(record)
    from agent.schemas.hyperparam_tuning import ExperimentRecord

    ExperimentRecord.model_validate(record)
    status = record.get("status")
    outer_failure = record.get("record_type") == "attempt_failure"
    if role == "unresolved" and not outer_failure:
        raise ValueError("Unresolved role requires a qualified pre-plan failure")
    completed = status in {"success", "failed_mode_collapse"} and not outer_failure
    if not completed and not outer_failure and status not in _UNSTAMPED:
        raise ValueError(f"Unqualified historical record producer: {status!r}")
    omitted = {"attempt_role"}
    # Only completed trial records stamped this key in the frozen producer.
    if not completed or role == "formal":
        omitted.add("is_trial")
    projected = deepcopy({key: value for key, value in record.items() if key not in omitted})
    return project_ordering(projected)


def _render_user(*, memory_history, **arguments):
    from .legacy_9b78d505cb11 import get_planner_user_prompt

    return get_planner_user_prompt(
        memory_history=[project_record(record) for record in memory_history],
        **deepcopy(arguments),
    )


def historical_attempt_role_v3():
    """Explicit replay provider; does not change any installation default."""
    from core.planner_strategy_identity import PlannerStrategyIdentity, source_fingerprint

    original = historical_ordering_v2()
    return replace(
        original,
        identity=PlannerStrategyIdentity(
            name=SELECTOR,
            version="3",
            content_sha256=source_fingerprint(
                {
                    "v2_identity.json": original.identity.model_dump_json().encode(),
                    "attempt_role_v3.py": Path(__file__).read_bytes(),
                }
            ),
        ),
        user_renderer=_render_user,
    )
