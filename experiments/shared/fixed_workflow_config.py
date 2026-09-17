"""Render a fixed workflow's shared JSON parameters into SIDERIUS arguments.

The experiment launcher owns run identity and information treatment. This
module only renders the same workflow and per-agent configuration for either
treatment arm; it never decides whether advice or analysis is available.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Literal

from agent.schemas.parameter_rules import ParameterRules
from pydantic import (
    BaseModel,
    ConfigDict,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
)

_FLAG = re.compile(r"--[a-z][a-z0-9_-]*\Z")
_LAUNCH_OWNED = frozenset(
    {
        "--mode",
        "--workspace",
        "--data_dir",
        "--run_name",
        "--task_composition",
        "--llm_config",
        "--experiment_arm",
        "--advice",
        "--advice_sha256",
        "--human_advice_file",
        "--ml_lit_review_enabled",
        "--no-ml_lit_review_enabled",
        "--data_analysis_enabled",
        "--no-data_analysis_enabled",
        "--workflow_parameter_rules",
        "--dry-run",
        "--help",
    }
)


class FixedWorkflowConfig(BaseModel):
    """One task composition, one agent-config JSON, and shared workflow flags."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["siderius-exp-fixed-workflow-v1"]
    task_composition: str
    agent_parameters: str
    agent_parameters_owner: Literal["siderius", "experiment"] = "siderius"
    parameters: dict[str, StrictStr | StrictInt | StrictFloat | StrictBool]
    workflow_parameter_rules: ParameterRules | None = None


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _contained_file(root: Path, raw: str, *, label: str) -> Path:
    relative = PurePosixPath(raw)
    if not raw or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label} must be a repository-relative path: {raw!r}")
    path = (root.resolve() / Path(*relative.parts)).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"{label} is missing or escapes its checkout: {raw!r}")
    return path


def render_siderius_args(
    config_path: Path, *, repository_root: Path, siderius_checkout: Path
) -> list[str]:
    """Validate and render arguments without choosing an information treatment."""

    payload = json.loads(
        config_path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
    )
    config = FixedWorkflowConfig.model_validate(payload)
    composition = _contained_file(
        repository_root, config.task_composition, label="task_composition"
    )
    agent_root = (
        repository_root
        if config.agent_parameters_owner == "experiment"
        else siderius_checkout
    )
    agent_config = _contained_file(
        agent_root, config.agent_parameters, label="agent_parameters"
    )
    # Check the agent file now, not after the run starts. Its detailed schema
    # remains owned by SIDERIUS at the pinned checkout.
    json.loads(
        agent_config.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
    )
    arguments = [
        "--task_composition",
        str(composition),
        "--llm_config",
        str(agent_config),
    ]
    if config.workflow_parameter_rules is not None:
        arguments.extend(
            (
                "--workflow_parameter_rules",
                config.workflow_parameter_rules.model_dump_json(exclude_none=True),
            )
        )
    for flag, value in config.parameters.items():
        if (
            not _FLAG.fullmatch(flag)
            or flag in _LAUNCH_OWNED
            or flag.startswith("--human_advice_")
        ):
            raise ValueError(f"invalid or launch-owned workflow parameter: {flag!r}")
        if isinstance(value, bool):
            if not value:
                raise ValueError(f"boolean workflow parameter must be true: {flag}")
            arguments.append(flag)
        else:
            rendered = str(value)
            if not rendered or "\n" in rendered or "\r" in rendered:
                raise ValueError(f"invalid workflow parameter value: {flag}")
            arguments.extend((flag, rendered))
    return arguments


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--siderius-checkout", type=Path, required=True)
    args = parser.parse_args()
    print(
        "\n".join(
            render_siderius_args(
                args.config,
                repository_root=args.repository_root,
                siderius_checkout=args.siderius_checkout,
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
