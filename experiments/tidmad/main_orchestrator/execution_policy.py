"""Project shared execution limits without imposing the fixed controller's topology."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt

from experiments.shared.checksum_manifest import sha256_file
from experiments.shared.fixed_workflow_config import render_siderius_args


class ExecutionPolicy(BaseModel):
    """Operator-owned native execution settings; deployment must enforce this binding."""

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
    """Validate the existing authority and require explicit shared settings.

    Missing fields fail before output creation. No controller iteration/round
    ceiling is copied; this artifact constrains execution, not action selection.
    """
    source = root / "experiments/tidmad/main_fixed_workflow/workflow.json"
    digest = sha256_file(source)
    # Reuse the existing duplicate-key, path, parameter-rule and flag checks.
    render_siderius_args(source, repository_root=root, siderius_checkout=checkout)
    raw = json.loads(source.read_text())["parameters"]
    required = {
        f"--{field}"
        for field in ExecutionPolicy.model_fields
        if field != "runtime_watchdog"
    }
    if missing := required - raw.keys():
        raise ValueError(f"missing explicit execution settings: {sorted(missing)}")
    fields = {
        field: raw[f"--{field}"]
        for field in ExecutionPolicy.model_fields
        if field != "runtime_watchdog"
    }
    enabled, disabled = "--runtime_watchdog" in raw, "--no-runtime_watchdog" in raw
    if enabled == disabled:
        raise ValueError("shared runtime watchdog must have one explicit enable state")
    fields["runtime_watchdog"] = enabled
    policy = ExecutionPolicy.model_validate(fields)
    if sha256_file(source) != digest:
        raise ValueError("fixed execution policy changed during preparation")
    return policy, digest
