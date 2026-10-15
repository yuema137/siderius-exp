"""Historical manual view for explicitly scheduler-disabled paper workspaces."""

import json
from dataclasses import replace
from pathlib import Path

from .paper_v4 import _manual_fixture
from .watchdog_policy_v10 import historical_watchdog_late_v10, historical_watchdog_v10

SELECTOR = "legacy-9b78d505cb11-paper-scheduler-off-v11"
LATE_SELECTOR = "legacy-9b78d505cb11-paper-late-scheduler-off-v11"


def _reject_scheduler_evidence(record):
    for field in ("params", "proposed_config"):
        config = record.get(field) or {}
        training = config.get("train_config") or {}
        if training.get("lr_schedule") is not None:
            raise ValueError(
                "Historical scheduler-disabled mode cannot render enabled lr_schedule"
            )
    history = record.get("training_history") or {}
    if history.get("learning_rates") is not None:
        raise ValueError(
            "Historical scheduler-disabled mode cannot render scheduled learning_rates"
        )


def _provider(*, late):
    from core.planner_strategy_identity import (
        PlannerStrategyIdentity,
        source_fingerprint,
    )

    original = historical_watchdog_late_v10() if late else historical_watchdog_v10()
    manual_bytes = (
        Path(__file__)
        .with_name("fixtures")
        .joinpath("native_scheduler_manual.json")
        .read_bytes()
    )
    qualified = json.loads(manual_bytes)
    previous = json.loads(_manual_fixture())["config_manuals"]["pre_pr"]
    previous["schemas"]["TrainConfig"]["properties"]["epochs"].pop("maximum")

    def manual_renderer(manual):
        if manual != qualified:
            raise ValueError("Unqualified v11 scheduler configuration manual")
        return original.render_config_manual(previous)

    def user_renderer(*, memory_history, **arguments):
        for record in memory_history:
            _reject_scheduler_evidence(record)
        return original.user_renderer(memory_history=memory_history, **arguments)

    return replace(
        original,
        identity=PlannerStrategyIdentity(
            name=LATE_SELECTOR if late else SELECTOR,
            version="11",
            content_sha256=source_fingerprint(
                {
                    "v10_identity.json": original.identity.model_dump_json().encode(),
                    "scheduler_manual_v11.py": Path(__file__).read_bytes(),
                    "native_scheduler_manual.json": manual_bytes,
                }
            ),
        ),
        config_manual_renderer=manual_renderer,
        user_renderer=user_renderer,
    )


def historical_scheduler_off_v11():
    return _provider(late=False)


def historical_scheduler_off_late_v11():
    return _provider(late=True)
