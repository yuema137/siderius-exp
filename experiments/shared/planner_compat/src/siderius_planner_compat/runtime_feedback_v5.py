"""Explicit historical runtime-refusal wording, without changing stored evidence."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from .paper_v4 import historical_paper_late_v4, historical_paper_v4

LEGACY_UPDATE = (
    "The measured runtime prediction exceeded the budget (or "
    "verification failed). Reduce the workload (steps, "
    "segmentation_size, portions, model size) — this rejection "
    "consumed an attempt, unlike pre-flight skips."
)


def project_record(record: dict[str, Any]) -> dict[str, Any]:
    """Convert only the declared producer; historical records remain unchanged."""
    result = deepcopy(record)
    memory = result.get("memory") or {}
    version = memory.get("runtime_feedback_version")
    if version is None:
        return result
    if version != "facts-v1":
        raise ValueError(f"Unqualified runtime feedback version: {version!r}")
    if (
        result.get("status") != "skipped_time_risk"
        or memory.get("verification_stage") != "in_subprocess"
    ):
        raise ValueError(
            "Runtime feedback projection requires an in-subprocess time refusal"
        )
    # Validate the underlying admission rather than fabricating a historical
    # strategy for an arbitrary user-authored memory entry.
    from core.runtime_control.records import AdmissionRecord

    admission = (result.get("runtime_verification") or {}).get("admission")
    if admission is not None:
        parsed = AdmissionRecord.model_validate(admission)
        if (
            parsed.decision != "rejected"
            or parsed.reason_code in {"record_only", "within_budget"}
            or parsed.stage == "pre_launch_screen"
        ):
            raise ValueError(
                "Runtime feedback projection requires a consistent in-subprocess refusal"
            )
    memory.pop("runtime_feedback_version")
    memory["memory_update"] = LEGACY_UPDATE
    return result


def _provider(*, late: bool):
    from core.planner_strategy_identity import (
        PlannerStrategyIdentity,
        source_fingerprint,
    )

    original = historical_paper_late_v4() if late else historical_paper_v4()
    name = "legacy-9b78d505cb11-paper" + ("-late" if late else "") + "-runtime-v5"

    def render(*, memory_history, **arguments):
        return original.user_renderer(
            memory_history=[project_record(record) for record in memory_history],
            **arguments,
        )

    return replace(
        original,
        identity=PlannerStrategyIdentity(
            name=name,
            version="5",
            content_sha256=source_fingerprint(
                {
                    "v4_identity.json": original.identity.model_dump_json().encode(),
                    "runtime_feedback_v5.py": Path(__file__).read_bytes(),
                }
            ),
        ),
        user_renderer=render,
    )


def historical_runtime_v5():
    return _provider(late=False)


def historical_runtime_late_v5():
    return _provider(late=True)
