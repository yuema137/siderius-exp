"""Explicit paper manual projection after removal of the generic epoch ceiling."""

import json
from dataclasses import replace
from pathlib import Path

from .paper_v4 import _manual_fixture
from .runtime_verifier_v8 import historical_verifier_late_v8, historical_verifier_v8

SELECTOR = "legacy-9b78d505cb11-paper-epochs-v9"
LATE_SELECTOR = "legacy-9b78d505cb11-paper-late-epochs-v9"


def _provider(*, late: bool):
    from core.planner_strategy_identity import (
        PlannerStrategyIdentity,
        source_fingerprint,
    )

    original = historical_verifier_late_v8() if late else historical_verifier_v8()
    fixture = _manual_fixture()
    qualified = json.loads(fixture)["config_manuals"]["pre_pr"]
    maximum = qualified["schemas"]["TrainConfig"]["properties"]["epochs"].pop("maximum")
    if maximum != 100:
        raise ValueError("Frozen paper epoch maximum changed")

    def render_manual(manual: dict) -> str:
        if manual != qualified:
            raise ValueError(
                "Unqualified v9 paper configuration manual: expected only removal "
                "of TrainConfig.epochs.maximum from the frozen reviewed schema"
            )
        # Delegate the output to the existing era owner, never reconstruct it
        # from a possibly reordered incoming dictionary.
        return original.render_config_manual(
            json.loads(fixture)["config_manuals"]["pre_pr"]
        )

    return replace(
        original,
        identity=PlannerStrategyIdentity(
            name=LATE_SELECTOR if late else SELECTOR,
            version="9",
            content_sha256=source_fingerprint(
                {
                    "v8_identity.json": original.identity.model_dump_json().encode(),
                    "epoch_manual_v9.py": Path(__file__).read_bytes(),
                    "paper_ligo_boundary.json": fixture,
                }
            ),
        ),
        config_manual_renderer=render_manual,
    )


def historical_epochs_v9():
    return _provider(late=False)


def historical_epochs_late_v9():
    return _provider(late=True)
