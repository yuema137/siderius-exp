"""Explicit historical mode preserves prompts without rewriting new records."""

from copy import deepcopy

import pytest
from siderius_planner_compat import current_legacy
from siderius_planner_compat.attempt_role_check import cases, check
from siderius_planner_compat.attempt_role_v3 import project_record

from agent.schemas.hyperparam_tuning import ExperimentRecord


def test_current_producers_and_final_prompts_match_historical_reference():
    result = check()
    assert result["producer_cases"] == 15
    assert result["final_prompt_pairs"] == 30
    assert result["api_calls"] == 0


def test_legacy_records_remain_unchanged_and_unknown_producers_are_refused():
    old = cases()[0]["expected_record"]
    assert project_record(old) == old
    unknown = deepcopy(old) | {
        "status": "future_failure",
        "attempt_role": "trial",
        "is_trial": True,
    }
    with pytest.raises(ValueError, match="future_failure"):
        project_record(unknown)


def test_projection_is_opt_in_and_does_not_change_default_provider():
    from agent.planner_strategy import resolve_planner_strategy

    assert resolve_planner_strategy(None).identity.name == current_legacy().identity.name
    assert (
        resolve_planner_strategy(None).identity.content_sha256
        == current_legacy().identity.content_sha256
    )
    # No adapter runs when records are read through the ordinary schema.
    current = deepcopy(cases()[1]["raw"]) | {"attempt_role": "trial", "is_trial": True}
    assert ExperimentRecord.model_validate(current).is_trial is True
