"""Bind tutorial copies to their prior planner and verify both installed providers."""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

from agent.planner_strategy import resolve_planner_strategy
from core.planner_strategy_identity import PlannerStrategyIdentity
from workflows.llm_config import WorkflowLLMConfig

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


def verify_planner_setup(
    config: Path, infra: Path, *, environment: dict[str, str]
) -> PlannerStrategyIdentity:
    """Resolve locally in both interpreters, without constructing an LLM client.

    Existing user configs are read only. Infra remains the authority for explicit
    selections or installed defaults. Child diagnostics are not echoed because
    an external config/provider could put sensitive values in its exception.
    """
    exp = Path(__file__).resolve().parents[2]
    repair = (
        f"In {exp}, run uv sync --group dev --group tutorial --frozen. "
        "Then install the same exp planner package into infra: "
        f"uv pip install --python {shlex.quote(str(infra / '.venv/bin/python'))} "
        f"{shlex.quote(str(exp / 'experiments/shared/planner_compat'))}. "
        "Check tune.planner_strategy in your llm/agents.json; "
        "install your selected provider in both environments if using a custom strategy."
    )
    routing = WorkflowLLMConfig.from_json(str(config))
    selection = routing.tune.planner_strategy if routing.tune else None
    try:
        expected = resolve_planner_strategy(selection).identity
    except (ValueError, TypeError, ImportError):
        raise ValueError(f"Exp cannot load the selected planner. {repair}") from None
    script = (
        "import sys; "
        "from workflows.llm_config import WorkflowLLMConfig; "
        "from agent.planner_strategy import resolve_planner_strategy; "
        "c = WorkflowLLMConfig.from_json(sys.argv[1]); "
        "s = c.tune.planner_strategy if c.tune else None; "
        "print(resolve_planner_strategy(s).identity.model_dump_json())"
    )
    try:
        result = subprocess.run(
            [str(infra / ".venv/bin/python"), "-c", script, str(config)],
            cwd=infra,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        actual = PlannerStrategyIdentity.model_validate_json(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError, ValueError):
        raise ValueError(f"Infra cannot load the selected planner. {repair}") from None
    if actual != expected:
        raise ValueError(
            f"Exp and infra loaded different planner identities. {repair} "
            "Do not resume an existing run after changing its strategy."
        )
    return expected
