"""Explicit pre-#447 planner input projection; never rewrite persisted evidence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

SELECTOR = "legacy-9b78d505cb11-ordering-v2"

# Frozen producer vocabulary from infra d116d156, not a live execution policy.
_ORDERING_FIELDS = frozenset(
    {
        "proposed_order_strategy",
        "proposed_file_order",
        "ordering_proposal_rejected",
        "ordering_proposal_rejection_reason",
        "override_order_strategy",
        "override_file_order",
        "resolved_order_strategy",
        "resolved_file_order",
        "ordering_resolution_source",
    }
)
_UNSTAMPED_SKIP_STATUSES = frozenset(
    {
        "skipped_oom_risk",
        "skipped_time_risk",
        "skipped_schema_violation",
        "skipped_resource_admission",
        "skipped_infrastructure_failure",
    }
)


def project_record(record: dict[str, Any]) -> dict[str, Any]:
    """Project a raw saved record to the qualified pre-#447 producer format.

    Missing/None observations remain historical inputs, unchanged. A present
    observation is validated by its infra owner. Filtering retains insertion
    order and does not discard unknown scientific or diagnostic fields.
    """
    observation = record.get("ordering_observation")
    if observation is None:
        return deepcopy(record)

    from agent.schemas.ordering import OrderingObservation

    observed = OrderingObservation.model_validate(observation)
    observed.validate_selection(
        record.get("resolved_order_strategy"),
        record.get("resolved_file_order"),
        record.get("ordering_resolution_source"),
    )
    outer_failure = record.get("record_type") == "attempt_failure"
    status = record.get("status")
    if observed.selection_state == "unresolved":
        if not outer_failure or observed.refused_before_phase is not None:
            raise ValueError(
                "Unqualified unresolved producer: expected an outer attempt failure"
            )
        remove_selection = True
    elif outer_failure:
        if observed.refused_before_phase is not None:
            raise ValueError(
                "Outer attempt failure cannot also claim a phase admission refusal"
            )
        # A post-resolution provider outage can share an infrastructure status
        # with admission. Its ordering WAS stamped before #447; preserve it.
        remove_selection = False
    elif status in _UNSTAMPED_SKIP_STATUSES:
        if observed.refused_before_phase is None and not (
            status == "skipped_time_risk"
            and (record.get("memory") or {}).get("verification_stage")
            == "in_subprocess"
        ):
            raise ValueError(
                "Unqualified skip: expected explicit refusal or measured rejection"
            )
        remove_selection = True
    else:
        if observed.refused_before_phase is not None:
            raise ValueError("A non-refusal record cannot claim a refused phase")
        remove_selection = False

    omitted = {"ordering_observation"}
    if remove_selection:
        omitted.update(_ORDERING_FIELDS)
    return deepcopy({key: value for key, value in record.items() if key not in omitted})


def _render_user(*, memory_history, **arguments):
    from .legacy_9b78d505cb11 import get_planner_user_prompt

    # The archived renderer is not changed. Only its input representation is
    # adapted, and the caller's records remain available for audit unchanged.
    return get_planner_user_prompt(
        memory_history=[project_record(record) for record in memory_history],
        **deepcopy(arguments),
    )


def historical_ordering_v2():
    """Load an explicit version, preserving v1 and the installation default."""
    from core.planner_strategy_identity import (
        PlannerStrategyIdentity,
        source_fingerprint,
    )

    from . import current_legacy

    original = current_legacy()
    return replace(
        original,
        identity=PlannerStrategyIdentity(
            name=SELECTOR,
            version="2",
            content_sha256=source_fingerprint(
                {
                    "v1_identity.json": original.identity.model_dump_json().encode(),
                    "ordering_v2.py": Path(__file__).read_bytes(),
                }
            ),
        ),
        user_renderer=_render_user,
    )
