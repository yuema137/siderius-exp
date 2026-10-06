"""Run with the qualified infra environment and normally installed exp package."""

import json
from copy import deepcopy
from importlib.resources import files

import pytest
from pydantic import ValidationError
from siderius_planner_compat.ordering_check import check, emit_case
from siderius_planner_compat.ordering_v2 import project_record


def cases():
    return json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/ordering_producer_boundary.json")
        .read_text()
    )["cases"]


def test_actual_producers_and_final_prompts_match_the_pre_447_reference():
    result = check()
    assert result["producer_cases"] == 15
    assert len(result["pairs"]) == 17
    assert result["api_calls"] == 0


def test_unknown_and_scientific_payloads_survive_without_aliasing():
    raw = emit_case(cases()[0])
    raw["future_scientific_evidence"] = {"samples": [1, 2]}
    before = deepcopy(raw)
    projected = project_record(raw)
    projected["future_scientific_evidence"]["samples"].append(3)
    assert raw == before


@pytest.mark.parametrize(
    "change",
    [
        {"selection_state": "unresolved"},
        {"selection_state": "selected", "refused_before_phase": "inference"},
        {"selection_state": "selected", "unknown_new_semantics": True},
    ],
)
def test_contradictory_or_future_evidence_is_not_silently_discarded(change):
    raw = emit_case(cases()[0])
    raw["ordering_observation"] = change
    with pytest.raises((ValueError, ValidationError)):
        project_record(raw)


def test_infrastructure_status_does_not_erase_selected_outer_failure():
    inputs = {case["id"]: case for case in cases()}
    selected = emit_case(inputs["provider-after-selection"])
    refusal = emit_case(inputs["measurement-preflight"])
    assert selected["status"] == refusal["status"]
    assert project_record(selected)["resolved_order_strategy"] == "sequential"
    assert "resolved_order_strategy" not in project_record(refusal)


def test_missing_observation_does_not_trigger_status_based_projection():
    old = {"status": "skipped_resource_admission", "resolved_order_strategy": "shuffle"}
    assert project_record(old) == old
    explicit_none = old | {"ordering_observation": None}
    assert project_record(explicit_none) == explicit_none


def test_unresolved_unknown_producer_is_refused():
    raw = emit_case(
        next(case for case in cases() if case["id"] == "outer-before-selection")
    )
    raw.pop("record_type")
    with pytest.raises(ValueError, match="Unqualified unresolved producer"):
        project_record(raw)


def test_empty_history_and_existing_provider_identity_are_preserved():
    from siderius_planner_compat import current_legacy
    from siderius_planner_compat.ordering_v2 import historical_ordering_v2

    old = current_legacy()
    assert old.identity.content_sha256 == (
        "0c36e016618dbc3d2d16000cdf4eedc1e49f8759e5bf886129866be760d4acde"
    )
    assert historical_ordering_v2().user_renderer(
        memory_history=[], current_round=1, max_rounds=3
    ) == old.user_renderer(memory_history=[], current_round=1, max_rounds=3)
