"""Execution bounds for the orchestration condition, derived not invented.

The caller selects its own actions — that is what makes it an orchestrator —
but it runs inside the same execution limits the fixed workflow ran under.
Those limits are read from
`experiments/phyts_tess/main_fixed_workflow/workflow.json` rather than
restated here, so the two conditions are comparable **by construction**: a
budget cannot drift between them without the file that defines both changing.

What is deliberately NOT carried over is the controller's topology —
iteration and round ceilings, the trial pin. Those select actions, and
selecting actions is the caller's job. This artifact constrains execution.

This mirrors `experiments/tidmad/main_orchestrator/execution_policy.py`,
which is the same mechanism against that task's own workflow file. The two
are not shared: consolidating them means editing the TIDMAD orchestrator
mid-campaign, which is a change for its owner to make, not this one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt

from experiments.shared.checksum_manifest import sha256_file
from experiments.shared.fixed_workflow_config import render_siderius_args

__all__ = ["WORKFLOW_RELATIVE_PATH", "ExecutionPolicy", "resolve_execution_policy"]

WORKFLOW_RELATIVE_PATH = Path(
    "experiments/phyts_tess/main_fixed_workflow/workflow.json"
)


class ExecutionPolicy(BaseModel):
    """Operator-owned native execution settings the deployment must enforce."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_epochs: StrictInt = Field(gt=0)
    trial_max_epochs: StrictInt = Field(gt=0)
    formal_max_epochs: StrictInt = Field(gt=0)
    trial_time_budget_minutes: StrictInt = Field(gt=0)
    formal_time_budget_minutes: StrictInt = Field(gt=0)
    trial_vram_budget_gb: StrictInt = Field(gt=0)
    formal_vram_budget_gb: StrictInt = Field(gt=0)
    formal_training_scope_source: Literal["operator", "agent"]
    formal_portion: StrictFloat = Field(gt=0, le=1)
    formal_train_portion: StrictFloat = Field(gt=0, le=1)
    formal_eval_portion: StrictFloat = Field(gt=0, le=1)
    training_budget_reserve_fraction: StrictFloat = Field(ge=0, lt=1)
    runtime_watchdog: StrictBool


def resolve_execution_policy(root: Path, checkout: Path) -> tuple[ExecutionPolicy, str]:
    """Read the fixed workflow's settings, refusing anything left implicit.

    Every bound must be stated in `workflow.json`. A missing one fails here,
    before any deployment directory exists, rather than surfacing as a default
    the operator never chose.
    """
    source = root / WORKFLOW_RELATIVE_PATH
    digest = sha256_file(source)
    # Reuse the workflow loader's own duplicate-key, path and flag checks
    # rather than re-deriving which keys are legal.
    render_siderius_args(source, repository_root=root, siderius_checkout=checkout)
    raw = json.loads(source.read_text(encoding="utf-8"))["parameters"]

    required = {
        f"--{field}"
        for field in ExecutionPolicy.model_fields
        if field != "runtime_watchdog"
    }
    if missing := required - raw.keys():
        raise ValueError(f"missing explicit execution settings: {sorted(missing)}")
    fields: dict[str, object] = {
        field: raw[f"--{field}"]
        for field in ExecutionPolicy.model_fields
        if field != "runtime_watchdog"
    }

    # The watchdog is a pair of mutually exclusive flags, not a value. Both or
    # neither means the operator never actually chose, so refuse rather than
    # picking one.
    enabled = "--runtime_watchdog" in raw
    disabled = "--no-runtime_watchdog" in raw
    if enabled == disabled:
        raise ValueError(
            "the runtime watchdog must be explicitly enabled or disabled in "
            f"{WORKFLOW_RELATIVE_PATH}"
        )
    fields["runtime_watchdog"] = enabled

    policy = ExecutionPolicy.model_validate(fields)
    if sha256_file(source) != digest:
        raise ValueError("the fixed workflow changed while preparation was reading it")
    return policy, digest
