"""Bind tutorial copies to their prior planner and verify both installed providers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from workflows.llm_config import WorkflowLLMConfig

from tutorials.shared.planner_setup import verify_planner_setup

# The prior tutorial pin (349b6cd6) used this exact planner source snapshot.
TUTORIAL_PLANNER = "legacy-9b78d505cb11-v1"


def copy_llm_config(source: Path, destination: Path) -> None:
    """Declare the previous strategy in a new copy; preserve explicit routing."""
    data = json.loads(source.read_text())
    WorkflowLLMConfig.model_validate(data)
    if data.get("tune") is None:
        data["tune"] = {}
    if data["tune"].get("planner_strategy") is None:
        data["tune"]["planner_strategy"] = TUTORIAL_PLANNER
    with destination.open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")


__all__ = ["TUTORIAL_PLANNER", "copy_llm_config", "subprocess", "verify_planner_setup"]
