"""Storage v7 and preflight v6 compose without concealing corrected evidence."""

from copy import deepcopy

import pytest
import torch

pytest.importorskip("core.preflight_estimation")

from agent.schemas.preflight import StaticPreflightEvidence
from agent.skills.evaluate_vram_skill.batch_resolver import resolve_inference_decision
from agent.skills.evaluate_vram_skill.estimation_inputs import observe_phase
from agent.skills.evaluate_vram_skill.evidence import preflight_memory_fields
from agent.skills.evaluate_vram_skill.preflight_adapter import adapt_result
from agent.skills.evaluate_vram_skill.preflight_worker_main import _classify
from agent.skills.evaluate_vram_skill.structural_probe import probe_activation_footprint
from core.preflight_estimation import bind_preflight_estimator, estimate_phase
from core.runtime_control.provenance import (
    assess_cache_state,
    capture_storage_provenance,
)
from siderius_planner_compat.legacy_storage_4e46ced5 import classify_cache_state
from siderius_planner_compat.self_check import _CaptureBridge
from siderius_preflight_compat import historical_profile

from experiments.shared.planner_compat.tests.test_static_preflight_v6 import (
    passing_record,
)
from experiments.shared.planner_compat.tests.test_storage_provenance_v7 import (
    _arguments,
    requires_current_producer,
)


@requires_current_producer
@pytest.mark.parametrize("late", [False, True])
def test_both_new_evidence_streams_restore_one_historical_request(late, tmp_path):
    current = passing_record()
    profile = historical_profile()
    shared = torch.nn.Linear(2, 2)
    model = torch.nn.Sequential(shared, shared, shared, shared)
    with bind_preflight_estimator(profile):
        decision = resolve_inference_decision(
            model,
            None,
            185 * 1024**2 + 256,
            candidate_batches=(7, 4, 1),
            supplied_probe=torch.zeros(1, 2),
        )
        evidence = StaticPreflightEvidence(
            version="static-preflight-v2",
            estimator_identity=profile.identity(),
            phases=(decision,),
        )
        probe = probe_activation_footprint(
            model,
            None,
            torch.zeros(decision.batch_size, 2),
            None,
            "inference",
        )
        estimate = estimate_phase(
            observe_phase(probe, model=model, batch_size=decision.batch_size)
        )
        worker = _classify(
            {
                "status": "success",
                "feasible": True,
                "static_preflight_evidence": evidence.model_dump(mode="json"),
                "estimated_gb": round(estimate.diagnostic_bytes / 1024**3, 3),
                "limit_gb": decision.vram_cap_bytes / 1024**3,
                "inference_batch": decision.batch_size,
            }
        )
    current["memory"].update(preflight_memory_fields(adapt_result(worker)))
    current["memory"]["vram_estimate_gb"] = worker["estimated_gb"]
    current["memory"]["vram_budget_gb"] = worker["limit_gb"]
    data = tmp_path / "fixture.bin"
    data.write_bytes(b"x" * 100)
    storage = capture_storage_provenance(str(tmp_path), [str(data)])
    assessment = assess_cache_state(
        0,
        storage["expected_on_disk_bytes"],
        process_read_bytes_scope=storage["process_read_bytes_scope"],
        process_read_bytes_reason=storage["process_read_bytes_reason"],
    )
    storage.update(
        bytes_read_from_storage=0,
        cache_state=assessment.state,
        cache_state_unknown_reason=assessment.unknown_reason,
        rss_bytes_before_setup=None,
        rss_bytes_after_setup=None,
    )
    current["runtime_verification"] = {
        "timestamp": "2026-10-07T00:00:00Z",
        "storage": storage,
    }
    historical = deepcopy(current)
    historical["memory"].pop("static_preflight_evidence")
    historical["memory"].pop("preflight_outcome")
    old_storage = historical["runtime_verification"]["storage"]
    old_storage["cache_state"] = classify_cache_state(
        0,
        old_storage["expected_raw_bytes"],
        filesystem_type=old_storage["filesystem_type"],
    )
    for key in (
        "expected_on_disk_bytes",
        "process_read_bytes_scope",
        "process_read_bytes_reason",
        "cache_state_unknown_reason",
    ):
        old_storage.pop(key)
    before = deepcopy(current)
    prefix = "legacy-9b78d505cb11-paper" + ("-late" if late else "")
    requests = []
    for suffix, record in (("runtime-v5", historical), ("storage-v7", current)):
        bridge = _CaptureBridge()
        bridge.plan(
            **(
                _arguments()
                | {"planner_strategy": f"{prefix}-{suffix}", "memory_history": [record]}
            )
        )
        assert len(bridge.captures) == 1
        requests.append(bridge.captures[0])
    assert requests[0] == requests[1]
    assert current == before
