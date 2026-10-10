"""Historical presentation uses the checkpoint, never corrected execution events."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from agent.prompt_templates.tuner.rendering import render_execution_provenance_block
from agent.schemas.execution_provenance import ExecutionProvenance, ResolutionEvent
from siderius_prompt_compat.provenance_0ab15736 import render_plan_resolution_checkpoint


def _event(proposed="10", executed="4"):
    return ResolutionEvent(
        field_path="train_cfg.epochs",
        proposed=proposed,
        executed=executed,
        authority="max_epochs_bound",
    )


def _provenance(actual, historical):
    # Also exercises this pure renderer against the old API: only the new
    # framework producer populates this field during a real run.
    return ExecutionProvenance(events=actual).model_copy(
        update={"plan_resolution_events": historical}
    )


def test_restored_authored_value_keeps_old_nonempty_block():
    value = _provenance((), (_event(),))
    before = value.model_dump()
    assert render_execution_provenance_block(value) == ""
    rendered = render_plan_resolution_checkpoint(value)
    assert (
        "train_cfg.epochs: proposed 10 -> EXECUTED 4   [--max_epochs bound]" in rendered
    )
    assert value.model_dump() == before
    assert value.events == ()


def test_actual_disagreement_does_not_replace_recorded_empty_checkpoint():
    value = _provenance((_event(),), ())
    before = value.model_dump()
    assert "EXECUTED 4" in render_execution_provenance_block(value)
    assert render_plan_resolution_checkpoint(value) == ""
    assert value.model_dump() == before
    assert value.events == (_event(),)


@pytest.mark.parametrize("value", [ExecutionProvenance(), SimpleNamespace(events=())])
def test_absent_or_null_checkpoint_refuses_even_when_actual_events_empty(value):
    with pytest.raises(ValueError, match="recorded plan-resolution checkpoint"):
        render_plan_resolution_checkpoint(value)


def test_no_provenance_renders_no_block():
    assert render_plan_resolution_checkpoint(None) == ""


def test_historical_renderer_does_not_reenter_native_boundary():
    with patch(
        "agent.prompt_templates.tuner.rendering.render_execution_provenance_block",
        side_effect=AssertionError(
            "Historical rendering must not call native renderer"
        ),
    ):
        assert "EXECUTED 4" in render_plan_resolution_checkpoint(
            _provenance((), (_event(),))
        )
