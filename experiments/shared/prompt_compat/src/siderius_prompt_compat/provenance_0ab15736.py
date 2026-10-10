"""Frozen paper-era execution-provenance text and explicit checkpoint selection.

The renderer and authority labels are copied from infra 0ab1573602c708ddd182432ad4d0e43ae4828c53.
All four paper reference revisions contain identical selected source bytes.
"""

from typing import Any

AUTHORITY_DESCRIPTIONS: dict[str, str] = {
    "operator_plan_overrides": "operator plan_overrides lock",
    "round_mode_override_chain": "round-mode override chain (trial lockout / formal inheritance)",
    "task_declared_objective": "task-declared objective",
    "parameter_rules": "task/workflow-declared parameter rules",
    "partial_scope_strategy_normalization": "partial data scope normalization",
    "max_epochs_bound": "--max_epochs bound",
    "forced_model_type": "forced model type",
    "unattributed": "resolved after the plan was authored (step not registered)",
}


def render_execution_provenance_block(provenance: Any) -> str:
    """What the framework RESOLVED after the plan was authored.

    Renders the empty string in the common case — a run whose authored plan
    survived resolution intact has nothing to correct, and its prompt bytes
    must not move. The block appears only when the planner's prose and the
    executed configuration actually DISAGREE.

    The block is worded as an authority, not as a hint. The reflector is
    reading a hypothesis written before any of these overrides happened; told
    only the values, a model reconciles the two by averaging them, and the
    witnessed defect (F15) is precisely a reflection that narrated a proposed
    loss as though it had run. So the block states which side governs, and
    names the step that overruled each field so the reflector can explain the
    difference rather than paper over it.
    """
    if provenance is None or not getattr(provenance, "events", ()):
        return ""

    lines = [
        "### RESOLVED EXECUTION AUTHORITY (governs — read this over the hypothesis)",
        "",
        "The hypothesis above is a PRE-EXECUTION PROPOSAL. The framework overruled",
        "the following value(s) after it was written, so the hypothesis does NOT",
        "describe what ran:",
        "",
    ]
    for event in provenance.events:
        described = AUTHORITY_DESCRIPTIONS.get(event.authority, event.authority)
        lines.append(
            f"  - {event.field_path}: proposed {event.proposed} "
            f"-> EXECUTED {event.executed}   [{described}]"
        )
    lines += [
        "",
        "Describe and judge what EXECUTED. Do not attribute this outcome to a",
        "proposed value that was overruled, and do not repeat such a value as if",
        "it had been used. Where the proposal and the executed configuration",
        "differ, the executed configuration is the fact.",
    ]
    return "\n".join(lines)


def render_plan_resolution_checkpoint(provenance: Any) -> str:
    """Render the recorded plan-only checkpoint without changing actual evidence."""
    if provenance is None:
        return ""
    events = getattr(provenance, "plan_resolution_events", None)
    if events is None:
        raise ValueError(
            "Historical provenance requires a recorded plan-resolution checkpoint"
        )
    return render_execution_provenance_block(
        provenance.model_copy(update={"events": events})
    )
