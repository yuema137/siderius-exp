"""Explicit historical display of qualified watchdog deadline-policy metadata."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from .epoch_manual_v9 import historical_epochs_late_v9, historical_epochs_v9
from .runtime_verifier_v8 import project_record as project_verifier

SELECTOR = "legacy-9b78d505cb11-paper-watchdog-v10"
LATE_SELECTOR = "legacy-9b78d505cb11-paper-late-watchdog-v10"
_OLD_FIELDS = frozenset(
    {
        "enabled",
        "grace_seconds",
        "poll_seconds",
        "floor_seconds",
        "safety_factor",
        "max_phase_seconds",
    }
)


def project_record(record: dict[str, Any]) -> dict[str, Any]:
    """Remove equivalent metadata only; retain the original execution evidence."""
    result = deepcopy(record)
    current = result
    for field in ("runtime_verification", "runtime_policy", "watchdog"):
        current = current.get(field)
        if current is None:
            return result
        if not isinstance(current, dict):
            raise TypeError(
                f"Historical watchdog projection requires a {field} mapping"
            )
    if current.keys() == _OLD_FIELDS:
        return result
    if current.keys() != _OLD_FIELDS | {"deadline_policy"}:
        raise ValueError("Unqualified watchdog fields in historical prompt projection")
    selection = current["deadline_policy"]
    if selection not in {"budget-ceiling-v1", "forecast-tightening-v1"}:
        raise ValueError("Unknown watchdog deadline policy in historical projection")

    from core.runtime_control.session import WatchdogConfig

    # Strict validation rejects coercions; the complete field-set check above
    # prevents defaults or ignored extras from hiding producer changes.
    WatchdogConfig.model_validate(current, strict=True)
    if current["enabled"] and selection != "forecast-tightening-v1":
        raise ValueError("An enabled native watchdog has no historical deadline view")
    current.pop("deadline_policy")
    return result


def _deadline_sources() -> dict[str, bytes]:
    from core.runtime_control import watchdog_deadline, watchdog_policy

    return {
        name: Path(module.__file__).read_bytes()
        for name, module in (
            ("watchdog_deadline.py", watchdog_deadline),
            ("watchdog_policy.py", watchdog_policy),
        )
    }


def _qualified_deadline_sources() -> dict[str, bytes]:
    from core.planner_strategy_identity import source_fingerprint
    from core.runtime_control.session import WatchdogConfig

    qualification = Path(__file__).with_name("watchdog-qualification.json").read_bytes()
    result = {"watchdog-qualification.json": qualification}
    # The old API has no new policy metadata and retains its existing assembly
    # gate through v9. Only the new API needs this additional execution owner.
    if "deadline_policy" not in WatchdogConfig.model_fields:
        return result
    sources = _deadline_sources()
    allowed = {row["source_sha256"] for row in json.loads(qualification)["assemblies"]}
    if source_fingerprint(sources) not in allowed:
        raise ValueError("Watchdog deadline source has not been qualified for v10")
    return result | sources


def _provider(*, late: bool):
    from core.planner_strategy_identity import (
        PlannerStrategyIdentity,
        source_fingerprint,
    )

    original = historical_epochs_late_v9() if late else historical_epochs_v9()

    def render(*, memory_history, **arguments):
        return original.user_renderer(
            # Validate the explicit execution policy before removing its metadata.
            # Otherwise legacy forecast-only evidence would be revalidated as
            # native/no-ceiling. The inherited v8 pass then has nothing to strip.
            memory_history=[
                project_record(project_verifier(record)) for record in memory_history
            ],
            **arguments,
        )

    return replace(
        original,
        identity=PlannerStrategyIdentity(
            name=LATE_SELECTOR if late else SELECTOR,
            version="10",
            content_sha256=source_fingerprint(
                {
                    "v9_identity.json": original.identity.model_dump_json().encode(),
                    "watchdog_policy_v10.py": Path(__file__).read_bytes(),
                    **_qualified_deadline_sources(),
                }
            ),
        ),
        user_renderer=render,
    )


def historical_watchdog_v10():
    return _provider(late=False)


def historical_watchdog_late_v10():
    return _provider(late=True)
