"""#419: preserve paper request bytes without rewriting corrected runtime evidence."""

import hashlib
import inspect
import json
from copy import deepcopy
from importlib.resources import files
from pathlib import Path

import pytest
from core.runtime_control import provenance
from siderius_planner_compat.legacy_storage_4e46ced5 import classify_cache_state
from siderius_planner_compat.self_check import _CaptureBridge
from siderius_planner_compat.storage_provenance_v7 import project_record

REPO_ROOT = Path(__file__).resolve().parents[4]
_MATRIX = json.loads(
    files("siderius_planner_compat")
    .joinpath("fixtures/storage_reference_matrix.json")
    .read_text()
)
_CURRENT_PRODUCER_QUALIFIED = (
    hashlib.sha256(Path(provenance.__file__).read_bytes()).hexdigest()
    == _MATRIX["current_provenance_sha256"]
)
requires_current_producer = pytest.mark.skipif(
    not _CURRENT_PRODUCER_QUALIFIED,
    reason="Requires the explicitly qualified #419 infra producer",
)


def _arguments():
    from agent.prompt_templates.tuner.rendering import TunerTaskRender
    from execute_tools.evaluation_metric import MetricSpec, PresenceScoreabilityContract

    package = files("siderius_planner_compat")
    fixture = json.loads(
        package.joinpath("fixtures/current_legacy_boundary.json").read_text()
    )
    manual = json.loads(
        package.joinpath("fixtures/paper_ligo_boundary.json").read_text()
    )
    return fixture["base_arguments"] | {
        "config_manual": manual["config_manuals"]["historical"],
        "task_render": TunerTaskRender.model_validate(fixture["task_render"]),
        "metric_spec": MetricSpec.model_validate(
            fixture["metric_spec"]
            | {
                "scoreability": PresenceScoreabilityContract.model_validate(
                    fixture["metric_spec"]["scoreability"]
                )
            }
        ),
    }


def _current_record(historical):
    result = deepcopy(historical)
    storage = (result.get("runtime_verification") or {}).get("storage")
    if not storage:
        return result
    storage.update(
        expected_on_disk_bytes=storage["expected_raw_bytes"],
        process_read_bytes_scope="unknown",
        process_read_bytes_reason=None,
        cache_state="unknown",
        cache_state_unknown_reason="process_counter_coverage_unknown",
    )
    return result


def _record(*, delta=0, physical_bytes=100, filesystem="ext4"):
    return {
        "exp_id": "storage_fixture",
        "status": "success",
        "params": {},
        "runtime_verification": {
            "storage": {
                "dataset_root": "/explicit-fixture-root",
                "file_count": 1,
                "files_present": 1,
                "expected_raw_bytes": physical_bytes,
                "total_file_bytes": physical_bytes,
                "filesystem_type": filesystem,
                "bytes_read_from_storage": delta,
                "cache_state": classify_cache_state(
                    delta, physical_bytes, filesystem_type=filesystem
                ),
                "rss_bytes_before_setup": 1024,
                "rss_bytes_after_setup": 2048,
            }
        },
    }


def _request(profile, history):
    bridge = _CaptureBridge()
    bridge.plan(
        **(_arguments() | {"planner_strategy": profile, "memory_history": history})
    )
    assert len(bridge.captures) == 1
    return bridge.captures[0]


def test_frozen_classifier_matches_the_audited_reference_source():
    """A changed historical function must not silently move paper rendering."""
    matrix = json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/storage_reference_matrix.json")
        .read_text()
    )
    assert (
        hashlib.sha256(inspect.getsource(classify_cache_state).encode()).hexdigest()
        == (matrix["classifier_source_sha256"])
    )


@requires_current_producer
@pytest.mark.parametrize("task", ["tess", "ligo", "project8", "tidmad"])
def test_archived_paper_structures_preserve_complete_requests(task):
    """Real archived records cover task shapes; synthetic new fields model #419 output.

    This is an offline rendering comparison, not a new scientific replay.
    TIDMAD's selected archive has no runtime storage and must remain unchanged.
    """
    fixture = (
        REPO_ROOT
        / "experiments/shared/prompt_compat/fixtures"
        / f"{task}-interpretation.json"
    )
    historical = json.loads(fixture.read_text())["arguments"]["tuning_output"][
        "all_records"
    ]
    current = [_current_record(record) for record in historical]
    original = deepcopy(current)
    prefix = "legacy-9b78d505cb11-paper" + ("-late" if task == "project8" else "")
    before = _request(prefix + "-preflight-v6", historical)
    after = _request(prefix + "-storage-v7", current)
    assert before == after
    assert [project_record(record) for record in current] == historical
    assert current == original
    if task != "tidmad":
        assert _request(prefix + "-preflight-v6", current) != before
    else:
        assert current == historical


@requires_current_producer
@pytest.mark.parametrize("late", [False, True])
@pytest.mark.parametrize(
    ("delta", "physical_bytes", "filesystem", "expected"),
    [
        (0, 100, "ext4", "warm_page_cache"),
        (49, 100, "ext4", "warm_page_cache"),
        (50, 100, "ext4", "cold_first_access"),
        (100, 100, "ext4", "cold_first_access"),
        (None, 100, "ext4", "unknown"),
        (0, 0, "ext4", "unknown"),
        (100, 100, "fuse.s3fs", "unknown"),
        (100, 100, "virtiofs", "unknown"),
    ],
)
def test_qualified_raw_inputs_restore_old_request(
    late, delta, physical_bytes, filesystem, expected
):
    """Coverage must affect current evidence while the explicit old view stays frozen."""
    historical = _record(
        delta=delta, physical_bytes=physical_bytes, filesystem=filesystem
    )
    assert historical["runtime_verification"]["storage"]["cache_state"] == expected
    current = _current_record(historical)
    current["runtime_verification"]["storage"].update(
        process_read_bytes_scope="incomplete",
        process_read_bytes_reason="loader reads in another process",
        cache_state_unknown_reason="loader reads in another process",
    )
    original = deepcopy(current)
    prefix = "legacy-9b78d505cb11-paper" + ("-late" if late else "")
    assert _request(prefix + "-storage-v7", [current]) == _request(
        prefix + "-preflight-v6", [historical]
    )
    # Dict equality cannot catch a rendering-order change; compare the exact JSON.
    assert json.dumps(project_record(current)) == json.dumps(historical)
    assert current == original


@requires_current_producer
@pytest.mark.parametrize(
    "defect",
    [
        "partial",
        "byte_basis",
        "coverage",
        "coverage_state",
        "unknown_reason",
        "future_field",
        "counter_type",
        "file_count",
        "storage_mapping",
        "verification_mapping",
    ],
)
def test_unqualified_storage_fails_before_provider_boundary(defect):
    current = _current_record(_record())
    storage = current["runtime_verification"]["storage"]
    if defect == "partial":
        storage.pop("expected_on_disk_bytes")
    elif defect == "byte_basis":
        storage["expected_on_disk_bytes"] = 101
    elif defect == "coverage":
        storage["process_read_bytes_scope"] = "future"
    elif defect == "coverage_state":
        storage.update(cache_state="warm_page_cache", cache_state_unknown_reason=None)
    elif defect == "unknown_reason":
        storage["cache_state_unknown_reason"] = None
    elif defect == "future_field":
        storage["future_metadata"] = 1
    elif defect == "counter_type":
        storage["bytes_read_from_storage"] = False
    elif defect == "file_count":
        storage["files_present"] = 2
    elif defect == "storage_mapping":
        current["runtime_verification"]["storage"] = []
    elif defect == "verification_mapping":
        current["runtime_verification"] = []
    bridge = _CaptureBridge()
    with pytest.raises((ValueError, TypeError)):
        bridge.plan(
            **(
                _arguments()
                | {
                    "planner_strategy": "legacy-9b78d505cb11-paper-storage-v7",
                    "memory_history": [current],
                }
            )
        )
    assert bridge.captures == []


@requires_current_producer
@pytest.mark.parametrize(
    ("delta", "state", "reason"),
    [
        (None, "cold_first_access", None),
        (0, "cold_first_access", None),
        (100, "warm_page_cache", None),
        (100, "unknown", "arbitrary reason"),
        (None, "unknown", "wrong unavailable-counter reason"),
    ],
)
def test_contradictory_complete_coverage_refuses_before_provider(delta, state, reason):
    """Review P2: never erase contradictory current evidence by relabeling it."""
    record = _current_record(_record(delta=delta))
    record["runtime_verification"]["storage"].update(
        process_read_bytes_scope="complete",
        cache_state=state,
        cache_state_unknown_reason=reason,
    )
    bridge = _CaptureBridge()
    with pytest.raises(ValueError, match="contradicts the qualified producer"):
        bridge.plan(
            **(
                _arguments()
                | {
                    "planner_strategy": "legacy-9b78d505cb11-paper-storage-v7",
                    "memory_history": [record],
                }
            )
        )
    assert bridge.captures == []


@requires_current_producer
@pytest.mark.parametrize(
    ("delta", "filesystem", "state", "reason"),
    [
        (0, "ext4", "warm_page_cache", None),
        (100, "ext4", "cold_first_access", None),
        (100, "fuse.s3fs", "cold_first_access", None),
        (None, "ext4", "unknown", "process_read_counter_unavailable"),
        (-1, "ext4", "unknown", "process_read_counter_decreased"),
    ],
)
def test_consistent_complete_coverage_keeps_historical_request(
    delta, filesystem, state, reason
):
    historical = _record(delta=delta, filesystem=filesystem)
    current = _current_record(historical)
    current["runtime_verification"]["storage"].update(
        process_read_bytes_scope="complete",
        cache_state=state,
        cache_state_unknown_reason=reason,
    )
    prefix = "legacy-9b78d505cb11-paper"
    assert _request(prefix + "-storage-v7", [current]) == _request(
        prefix + "-preflight-v6", [historical]
    )


def test_unqualified_current_producer_refuses_profile_construction(monkeypatch):
    """Source drift must change admission before any old-view rendering occurs."""
    from siderius_planner_compat.storage_provenance_v7 import historical_storage_v7

    original = Path.read_bytes

    def changed(path):
        value = original(path)
        return (
            value + b"# changed producer"
            if path == Path(provenance.__file__)
            else value
        )

    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(
        ValueError, match="Unqualified current storage provenance producer"
    ):
        historical_storage_v7()
