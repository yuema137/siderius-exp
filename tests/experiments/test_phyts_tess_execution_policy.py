"""The orchestration condition inherits the fixed workflow's execution bounds.

* ``test_the_policy_is_the_fixed_workflow_and_not_a_copy`` — comparability
  is the whole point. A hand-written bound here would let the two conditions
  diverge while both still ran and both still produced numbers, and the
  comparison would quietly mean something else.
* ``test_a_bound_left_implicit_is_refused`` — a missing setting must fail
  before any deployment directory exists, rather than arriving as a default
  nobody chose.
* ``test_the_watchdog_must_be_stated_either_way`` — the watchdog is a pair
  of mutually exclusive flags, so "absent" and "both" are the same kind of
  non-answer and neither may be silently resolved.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from experiments.phyts_tess.main_orchestrator.execution_policy import (
    WORKFLOW_RELATIVE_PATH,
    ExecutionPolicy,
    resolve_execution_policy,
)

EXP_ROOT = Path(__file__).resolve().parents[2]
CHECKOUT_ENV = "SIDERIUS_CHECKOUT"


def _checkout() -> Path:
    import os

    configured = os.environ.get(CHECKOUT_ENV)
    if not configured:
        pytest.skip(
            f"{CHECKOUT_ENV} is not set. This case resolves the workflow through "
            "the framework's own loader. Skipped means UNVERIFIED, not passed."
        )
    return Path(configured)


def _root_with(destination: Path, parameters: dict) -> Path:
    """A minimal repository root holding a mutated workflow.

    The workflow loader validates the paths its own file references before
    anything else, so those files have to exist here too — otherwise the
    mutation under test is never reached and the case passes for the wrong
    reason.
    """
    workflow = json.loads(
        (EXP_ROOT / WORKFLOW_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    workflow["parameters"] = parameters
    (destination / WORKFLOW_RELATIVE_PATH.parent).mkdir(parents=True, exist_ok=True)
    (destination / WORKFLOW_RELATIVE_PATH).write_text(
        json.dumps(workflow), encoding="utf-8"
    )
    for referenced in (workflow["task_composition"], workflow["agent_parameters"]):
        target = destination / referenced
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(EXP_ROOT / referenced, target)
    return destination


def test_the_policy_is_the_fixed_workflow_and_not_a_copy():
    """Every bound compared against the file that defines both conditions."""
    policy, digest = resolve_execution_policy(EXP_ROOT, _checkout())

    parameters = json.loads(
        (EXP_ROOT / WORKFLOW_RELATIVE_PATH).read_text(encoding="utf-8")
    )["parameters"]

    for field in ExecutionPolicy.model_fields:
        if field == "runtime_watchdog":
            continue
        assert getattr(policy, field) == parameters[f"--{field}"], (
            f"{field} differs from the fixed workflow; the orchestration "
            "condition must inherit its bounds, not restate them"
        )

    # The watchdog is off in this treatment, stated by its negative flag.
    assert policy.runtime_watchdog is False
    assert "--no-runtime_watchdog" in parameters
    assert len(digest) == 64


def test_a_bound_left_implicit_is_refused(tmp_path):
    """A stripped workflow must fail loudly, naming what is missing."""
    parameters = json.loads(
        (EXP_ROOT / WORKFLOW_RELATIVE_PATH).read_text(encoding="utf-8")
    )["parameters"]
    parameters.pop("--formal_eval_portion")

    with pytest.raises(Exception) as excinfo:
        resolve_execution_policy(_root_with(tmp_path / "exp", parameters), _checkout())
    assert "formal_eval_portion" in str(excinfo.value)


def test_the_watchdog_must_be_stated_either_way(tmp_path):
    """Neither flag, and both flags, are the same non-answer."""
    base = json.loads((EXP_ROOT / WORKFLOW_RELATIVE_PATH).read_text(encoding="utf-8"))[
        "parameters"
    ]

    for mutation in ("neither", "both"):
        parameters = json.loads(json.dumps(base))
        parameters.pop("--no-runtime_watchdog", None)
        if mutation == "both":
            parameters["--runtime_watchdog"] = True
            parameters["--no-runtime_watchdog"] = True

        with pytest.raises(Exception) as excinfo:
            resolve_execution_policy(
                _root_with(tmp_path / mutation, parameters), _checkout()
            )
        assert "watchdog" in str(excinfo.value).lower(), mutation
