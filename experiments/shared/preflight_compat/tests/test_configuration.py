"""Historical migration must explicitly disable new inference admission policy."""

from copy import deepcopy

import pytest

pytest.importorskip("core.inference_preflight_policy")

from siderius_preflight_compat.configuration import historical_task_composition


@pytest.mark.parametrize(
    "declaration,expected_bound",
    [({}, 3), ({"inference_preflight": {"mode": "static_only", "max_batches": 7}}, 7)],
)
def test_historical_copy_pins_static_only_without_changing_the_input(
    declaration, expected_bound
):
    """Fails if migration inherits native fallback, resets a bound, or aliases input."""
    original = {"task_name": "synthetic", "nested": {"value": 1}, **declaration}
    before = deepcopy(original)
    updated = historical_task_composition(original)
    assert updated["preflight_estimator"] == "legacy-078b23ca-preflight-v1"
    assert updated["inference_preflight"] == {
        "mode": "static_only",
        "max_batches": expected_bound,
    }
    assert historical_task_composition(updated) == updated
    updated["nested"]["value"] = 2
    updated["inference_preflight"]["max_batches"] = 99
    assert original == before


@pytest.mark.parametrize(
    "declaration",
    [
        {"preflight_estimator": "registered-state-v1"},
        {"inference_preflight": {"mode": "bounded_measurement", "max_batches": 3}},
        {"inference_preflight": {}},
        {"inference_preflight": None},
        {"inference_preflight": {"mode": "static_only", "max_batches": 0}},
        {"inference_preflight": {"mode": "static_only", "max_batches": True}},
        {"inference_preflight": {"mode": "static_only", "future_policy": "unknown"}},
    ],
)
def test_migration_does_not_silently_overwrite_or_repair_explicit_policy(declaration):
    """The helper must validate the declaration instead of discarding it before validation."""
    before = deepcopy(declaration)
    with pytest.raises(ValueError):
        historical_task_composition(declaration)
    assert declaration == before
