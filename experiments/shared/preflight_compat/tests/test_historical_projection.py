"""Do not conceal corrected native numbers behind a historical planner view."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("core.preflight_estimation")

import siderius_preflight_compat as compatibility
from core.preflight_estimation import (
    estimation_assembly_digest,
    resolve_preflight_estimator,
)
from siderius_planner_compat.self_check import _CaptureBridge
from siderius_planner_compat.static_preflight_v6 import (
    historical_preflight_v6,
    project_record,
)

from experiments.shared.planner_compat.tests.test_static_preflight_v6 import (
    passing_record,
    planner_arguments,
)


@pytest.fixture
def profile(monkeypatch):
    # Unit qualification only. Release qualification is a separate receipt.
    profile = replace(
        compatibility.historical_profile(),
        qualified_assemblies=frozenset({estimation_assembly_digest()}),
    )
    monkeypatch.setattr(compatibility, "historical_profile", lambda: profile)
    return profile


def version2_record(identity):
    record = passing_record()
    evidence = record["memory"]["static_preflight_evidence"]
    evidence["version"] = "static-preflight-v2"
    evidence["estimator_identity"] = identity.model_dump(mode="json")
    return record


@pytest.mark.parametrize("late", [False, True])
def test_qualified_historical_identity_keeps_full_request_bytes(profile, late):
    current = version2_record(profile.identity())
    before = deepcopy(current)
    archived = deepcopy(current)
    archived["memory"].pop("static_preflight_evidence")
    archived["memory"].pop("preflight_outcome")
    prefix = "legacy-9b78d505cb11-paper" + ("-late" if late else "")
    requests = []
    for version, record in (("runtime-v5", archived), ("preflight-v6", current)):
        bridge = _CaptureBridge()
        bridge.plan(
            **(
                planner_arguments()
                | {
                    "memory_history": [record],
                    "planner_strategy": f"{prefix}-{version}",
                }
            )
        )
        assert len(bridge.captures) == 1
        requests.append(bridge.captures[0])
    assert requests[0] == requests[1]
    assert current == before


def test_native_v2_is_rejected_without_rewriting_its_numeric_estimate(profile):
    current = version2_record(resolve_preflight_estimator().identity())
    current["memory"]["vram_estimate_gb"] = 0.625
    before = deepcopy(current)
    with pytest.raises(ValueError, match="exact qualified estimator identity"):
        project_record(current)
    assert current == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "other"),
        ("version", "2"),
        ("content_sha256", "f" * 64),
        ("assembly_sha256", "e" * 64),
    ],
)
def test_changed_identity_is_rejected(profile, field, value):
    current = version2_record(profile.identity().model_copy(update={field: value}))
    with pytest.raises(ValueError, match="qualified"):
        project_record(current)


def test_historical_refusal_remains_unqualified(profile):
    current = version2_record(profile.identity())
    current["memory"]["preflight_outcome"] = "STATIC_PREFLIGHT_REFUSAL"
    with pytest.raises(ValueError, match="Unqualified static preflight refusal"):
        project_record(current)


def test_historical_identity_does_not_authorize_a_different_formula(profile):
    current = version2_record(profile.identity())
    current["memory"]["static_preflight_evidence"]["phases"][0]["estimator"] = (
        "training_registered_state_v1"
    )
    with pytest.raises(ValueError, match="contradicts the phase formula"):
        project_record(current)


def test_v1_remains_usable_without_estimator_qualification():
    record = passing_record()
    assert "static_preflight_evidence" not in project_record(record)["memory"]


def test_configuration_source_change_invalidates_estimator_and_planner_identity(
    profile, monkeypatch
):
    """Policy migration is executable compatibility behavior, so its bytes must be pinned."""
    configuration = Path(compatibility.__file__).parent / "configuration.py"
    estimator_before = profile.identity()
    planner_before = historical_preflight_v6().identity
    read_bytes = Path.read_bytes

    def changed_source(path):
        source = read_bytes(path)
        return (
            source + b"\n# changed historical policy\n"
            if path == configuration
            else source
        )

    monkeypatch.setattr(Path, "read_bytes", changed_source)
    assert profile.identity().content_sha256 != estimator_before.content_sha256
    assert (
        historical_preflight_v6().identity.content_sha256
        != planner_before.content_sha256
    )
