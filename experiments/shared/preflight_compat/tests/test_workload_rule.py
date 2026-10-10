"""Historical workload selection must survive the native default correction."""

from dataclasses import replace

import pytest

registry = pytest.importorskip("core.preflight_estimation")

from agent.skills.evaluate_vram_skill import compute_intensity
from siderius_preflight_compat import historical_profile


def test_installed_historical_selection_preserves_exact_workload_boundary():
    profile = replace(
        historical_profile(),
        qualified_assemblies=frozenset({registry.estimation_assembly_digest()}),
    )
    with registry.bind_preflight_estimator(profile):
        assert compute_intensity.passes(2, 400000)
        assert not compute_intensity.passes(2, 400001)


def test_new_api_profile_commits_explicit_policy_and_detects_policy_change():
    if not hasattr(registry, "BatchSegmentationLimit"):
        pytest.skip("Pinned historical framework predates explicit workload rules")
    profile = replace(
        historical_profile(),
        qualified_assemblies=frozenset({registry.estimation_assembly_digest()}),
    )
    assert profile.workload_rule == registry.BatchSegmentationLimit(limit=800000)
    original = profile.identity().content_sha256
    assert replace(profile, workload_rule=None).identity().content_sha256 != original
    changed = replace(
        profile, workload_rule=registry.BatchSegmentationLimit(limit=800001)
    )
    assert changed.identity().content_sha256 != original
    with registry.bind_preflight_estimator(changed):
        assert compute_intensity.passes(1, 800001)


@pytest.mark.parametrize("late", [False, True])
def test_current_paper_profile_preserves_full_requests_with_historical_rule(late):
    if not hasattr(registry, "BatchSegmentationLimit"):
        pytest.skip("Current paper v9 requires the newer framework manual")
    from copy import deepcopy

    from siderius_planner_compat.self_check import _CaptureBridge

    from experiments.shared.planner_compat.tests.test_static_preflight_v6 import (
        planner_arguments,
    )
    from experiments.shared.preflight_compat.tests.test_historical_projection import (
        version2_record,
    )

    profile = historical_profile()
    current = version2_record(profile.identity())
    before = deepcopy(current)
    archived = deepcopy(current)
    archived["memory"].pop("static_preflight_evidence")
    archived["memory"].pop("preflight_outcome")
    strategy = "legacy-9b78d505cb11-paper-" + ("late-" if late else "") + "epochs-v9"
    requests = []
    for record in (archived, current):
        bridge = _CaptureBridge()
        bridge.plan(
            **(
                planner_arguments()
                | {"memory_history": [record], "planner_strategy": strategy}
            )
        )
        assert len(bridge.captures) == 1
        requests.append(bridge.captures[0])
    assert requests[0] == requests[1]
    assert current == before
