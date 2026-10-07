"""A bounded admission decision cannot disappear into a historical planner view."""

from copy import deepcopy

import pytest
from siderius_planner_compat.static_preflight_v6 import project_record


@pytest.mark.parametrize(
    "verification", [None, {}, "malformed", {"disposition": "admitted"}]
)
@pytest.mark.parametrize("static_fields", [False, True])
def test_verification_presence_refuses_before_legacy_history_early_return(
    verification, static_fields
):
    """Reject by presence, even when falsey, rather than hiding a new admission path."""
    record = {
        "memory": {
            "conclusion": "Keep this fact",
            "inference_verification": verification,
        }
    }
    if static_fields:
        record["memory"].update(
            preflight_outcome="COMPLETED_MEASUREMENT", static_preflight_evidence={}
        )
    before = deepcopy(record)
    with pytest.raises(ValueError, match="cannot accept inference_verification"):
        project_record(record)
    assert record == before


@pytest.mark.parametrize("late", [False, True])
@pytest.mark.parametrize("version", ["preflight-v6", "storage-v7"])
def test_all_historical_preflight_renderers_reject_before_provider_request(
    late, version
):
    """V7 must still reach the V6 guard after its storage projection."""
    pytest.importorskip("agent.schemas.preflight")
    from siderius_planner_compat.self_check import _CaptureBridge

    from experiments.shared.planner_compat.tests.test_static_preflight_v6 import (
        planner_arguments,
    )

    record = {"memory": {"inference_verification": None}}
    before = deepcopy(record)
    prefix = "legacy-9b78d505cb11-paper" + ("-late" if late else "")
    bridge = _CaptureBridge()
    with pytest.raises(ValueError, match="cannot accept inference_verification"):
        bridge.plan(
            **(
                planner_arguments()
                | {
                    "planner_strategy": f"{prefix}-{version}",
                    "memory_history": [record],
                }
            )
        )
    assert bridge.captures == []
    assert record == before
