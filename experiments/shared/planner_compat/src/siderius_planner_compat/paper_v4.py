"""Explicit paper-era planner representation, including its configuration manual."""

from __future__ import annotations

import json
from dataclasses import replace
from importlib.resources import files
from pathlib import Path

from .attempt_role_v3 import historical_attempt_role_v3

SELECTOR = "legacy-9b78d505cb11-paper-v4"
LATE_SELECTOR = "legacy-9b78d505cb11-paper-late-v4"


def _manual_fixture() -> bytes:
    return (
        files("siderius_planner_compat").joinpath("fixtures/paper_ligo_boundary.json").read_bytes()
    )


def render_manual(manual: dict, *, historical: str = "historical") -> str:
    """Accept only the two audited schemas, preserving the frozen old ordering.

    This is prompt representation only. Execution still validates against the
    current schema. Unknown schema changes require new qualification, not a
    best-effort deletion of properties.
    """
    manuals = json.loads(_manual_fixture())["config_manuals"]
    if manual != manuals["historical"] and manual != manuals["pre_pr"]:
        raise ValueError(
            "Unqualified paper configuration manual: expected the frozen historical "
            "or reviewed current schema. Qualify a new explicit profile before replay."
        )
    return json.dumps(manuals[historical], indent=2)


def historical_paper_v4():
    """Compose the manual and raw-history representations without changing defaults."""
    return _provider(SELECTOR, "historical")


def historical_paper_late_v4():
    """Project8 and analysis-on TIDMAD already used the later training schema."""
    return _provider(LATE_SELECTOR, "pre_pr")


def _provider(selector: str, manual_version: str):
    from functools import partial

    from core.planner_strategy_identity import PlannerStrategyIdentity, source_fingerprint

    original = historical_attempt_role_v3()
    return replace(
        original,
        identity=PlannerStrategyIdentity(
            name=selector,
            version="4",
            content_sha256=source_fingerprint(
                {
                    "v3_identity.json": original.identity.model_dump_json().encode(),
                    "paper_v4.py": Path(__file__).read_bytes(),
                    "paper_ligo_boundary.json": _manual_fixture(),
                    "manual_version": manual_version.encode(),
                }
            ),
        ),
        config_manual_renderer=partial(render_manual, historical=manual_version),
    )
