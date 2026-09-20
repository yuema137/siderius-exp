"""PhyTS TESS fixed-workflow experiment contract checks.

Each case names a defect nothing else would catch:

* ``test_the_two_arms_differ_only_in_information`` — the contrast is only
  valid if the arms are identical everywhere else. A budget or composition
  that drifted in one arm would still run, still produce numbers, and make
  the comparison mean something other than what it claims.
* ``test_only_the_full_arm_carries_advice_flags`` — a no-prior arm that
  emitted ``--advice`` would silently be a prior arm.
* ``test_the_declared_advice_digest_matches_the_artifact`` — the treatment
  pins a sha256 by hand. A later edit to the advice file leaves the pin
  stale, and only recomputing catches it.
* ``test_required_keys_follow_the_arm`` — the defect avoided during review:
  a hardcoded Data Analysis exclusion keeps excluding it after an arm
  enables it, so the run starts without the key it needs and fails only
  after the clock has begun.
* ``test_the_frozen_budget_values`` — the treatment values are the
  experiment's identity. A silent change makes two units incomparable while
  both still complete.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.shared.information_treatment import (
    ModuleState,
    resolve_information_treatment,
)
from experiments.shared.workflow_credentials import required_workflow_api_keys

EXP_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = EXP_ROOT / "experiments" / "phyts_tess" / "main_fixed_workflow"
TREATMENTS = EXP_ROOT / "experiments" / "phyts_tess" / "information_treatments"
ADVICE = EXPERIMENT / "advice.json"
WORKFLOW = EXPERIMENT / "workflow.json"
AGENTS = EXPERIMENT / "agents.json"

ARMS = {
    "no-prior": TREATMENTS / "main-fixed-no-prior.yaml",
    "full": TREATMENTS / "main-fixed-full.yaml",
}


def _resolve(arm: str):
    return resolve_information_treatment(
        ARMS[arm],
        repository_root=EXP_ROOT,
        adapter="siderius",
        required_modules=("literature_review", "data_analysis"),
    )


def test_the_two_arms_differ_only_in_information():
    """Same task package on both sides; the workflow config is shared outright."""
    packages = {arm: _resolve(arm).declaration.task_package for arm in ARMS}
    assert set(packages.values()) == {"tasks/phyts_tess"}, packages

    # There is ONE workflow.json. Not "two that agree" — one, so a budget
    # cannot drift between arms even in principle. This asserts that the
    # experiment never grew a second copy.
    assert sorted(p.name for p in EXPERIMENT.glob("workflow*.json")) == [
        "workflow.json"
    ]

    lit = {arm: _resolve(arm).module_states["literature_review"] for arm in ARMS}
    assert set(lit.values()) == {ModuleState.ENABLED}, (
        f"literature review must be enabled in BOTH arms, got {lit}; otherwise "
        "the contrast is a two-variable change"
    )


def test_only_the_full_arm_carries_advice_flags():
    no_prior = _resolve("no-prior").siderius_args()
    full = _resolve("full").siderius_args()

    assert "--advice" not in no_prior
    assert "--advice_sha256" not in no_prior
    assert "--no-data_analysis_enabled" in no_prior

    assert "--advice" in full
    assert "--advice_sha256" in full
    assert "--data_analysis_enabled" in full

    arms = {
        args[args.index("--experiment_arm") + 1]
        for args in (no_prior, full)
        if "--experiment_arm" in args
    }
    assert arms == {
        "phyts-tess-main-fixed-no-prior-v1",
        "phyts-tess-main-fixed-full-v1",
    }, f"each arm must carry its own identity, got {arms}"


def test_the_declared_advice_digest_matches_the_artifact():
    """The pin is hand-written; only recomputing can catch a stale one."""
    declared = _resolve("full").declaration.advice.sha256
    observed = hashlib.sha256(ADVICE.read_bytes()).hexdigest()
    assert declared == observed, (
        f"main-fixed-full.yaml pins {declared} but advice.json hashes to "
        f"{observed}; re-pin the treatment or restore the artifact"
    )


def test_the_advice_artifact_uses_only_recognised_keys():
    """An unrecognised key reaches no consumer and the loader refuses it.

    Checked against the framework's own constant rather than a copy, so this
    cannot drift from what the loader actually accepts.
    """
    from workflows.run_one_iteration import ADVICE_RECOGNISED_KEYS

    content = json.loads(ADVICE.read_text(encoding="utf-8"))
    substantive = {key for key in content if not key.startswith("_")}
    assert substantive <= set(ADVICE_RECOGNISED_KEYS), (
        f"unrecognised advice keys {sorted(substantive - set(ADVICE_RECOGNISED_KEYS))}"
    )
    assert substantive, "an advice artifact that injects nothing is refused at load"
    for key in substantive:
        value = content[key]
        joined = value if isinstance(value, str) else "\n".join(value)
        assert joined.strip(), f"advice key {key!r} is present but injects nothing"


def test_required_keys_follow_the_arm():
    """Derived from module state, never from a constant.

    A hardcoded exclusion would keep excluding Data Analysis after the full
    arm enabled it, and the run would start missing a key it needs and fail
    only once the clock had begun.
    """
    for arm in ARMS:
        treatment = _resolve(arm)
        disabled = frozenset(
            module
            for module, state in treatment.module_states.items()
            if state is ModuleState.DISABLED
        )
        expected_disabled = {"data_analysis"} if arm == "no-prior" else set()
        assert set(disabled) == expected_disabled, (arm, disabled)
        assert required_workflow_api_keys(AGENTS, disabled_roles=disabled)

    # The full arm enables Data Analysis, so the agent config must describe
    # that role. Enabling a module the config cannot route is a launch-time
    # failure that no treatment check would see.
    agents = json.loads(AGENTS.read_text(encoding="utf-8"))
    assert "data_analysis" in agents


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--num_iterations", 100),
        ("--max_rounds", 2),
        ("--trial_time_budget_minutes", 5),
        ("--formal_time_budget_minutes", 15),
        ("--trial_vram_budget_gb", 8),
        ("--formal_vram_budget_gb", 8),
        ("--formal_portion", 1.0),
        ("--formal_eval_portion", 1.0),
        ("--formal_training_scope_source", "agent"),
    ],
)
def test_the_frozen_budget_values(flag, value):
    """These values ARE the experiment's identity, so they are pinned here."""
    parameters = json.loads(WORKFLOW.read_text(encoding="utf-8"))["parameters"]
    assert parameters[flag] == value


def test_trial_portions_are_left_agent_controlled():
    """Omitted means agent-controlled; typing any of them freezes it.

    The experiment deliberately lets the agent choose its trial workload.
    Adding one of these keys would silently convert that to EXPERIMENT_FIXED
    while every other check here still passed.
    """
    parameters = json.loads(WORKFLOW.read_text(encoding="utf-8"))["parameters"]
    for flag in ("--trial_portion", "--train_portion", "--eval_portion"):
        assert flag not in parameters, (
            f"{flag} is present, which freezes what this experiment means to "
            "leave under agent control"
        )


def test_round_one_is_pinned_to_a_trial():
    """max_rounds=2 alone lets the planner make BOTH rounds formal.

    force_formal_round only guarantees the LAST round is formal. Without this
    override an iteration could contain two formal rounds and no trial, which
    is a different experiment that would still run to completion.
    """
    parameters = json.loads(WORKFLOW.read_text(encoding="utf-8"))["parameters"]
    overrides = json.loads(parameters["--plan_overrides"])
    assert overrides == {"is_trial": True}
