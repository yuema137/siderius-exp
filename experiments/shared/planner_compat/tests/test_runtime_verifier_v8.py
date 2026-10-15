"""Compare current session evidence with independently captured original sessions."""

import builtins
import hashlib
import json
from copy import deepcopy
from importlib.resources import files
from pathlib import Path

import pytest
from siderius_planner_compat.runtime_verifier_v8 import project_record
from siderius_planner_compat.self_check import _CaptureBridge

from experiments.shared.runtime_compat.replay import replay_cases

ROOT = Path(__file__).resolve().parents[2] / "runtime_compat"
TRACES = json.loads((ROOT / "fixtures/paper-finite-workloads.json").read_text())
ORIGINAL = json.loads((ROOT / "fixtures/paper-session-policies.json").read_text())


@pytest.fixture(scope="module")
def sessions():
    return replay_cases(
        TRACES, completion_policy="verified-prediction-v1", historical_verifier=True
    )


def _record(session):
    return {
        "status": "skipped_time_risk",
        "runtime_verification": {
            "runtime_policy": session["policy"],
            "components": {"training": session["component"]},
            "admission": session["admission"],
        },
    }


def _request(profile, record, *, config_manual=None):
    from agent.prompt_templates.tuner.rendering import TunerTaskRender
    from execute_tools.evaluation_metric import MetricSpec, PresenceScoreabilityContract

    package = files("siderius_planner_compat")
    fixture = json.loads(
        package.joinpath("fixtures/current_legacy_boundary.json").read_text()
    )
    manual = json.loads(
        package.joinpath("fixtures/paper_ligo_boundary.json").read_text()
    )
    arguments = fixture["base_arguments"] | {
        "config_manual": (
            manual["config_manuals"]["historical"]
            if config_manual is None
            else config_manual
        ),
        "task_render": TunerTaskRender.model_validate(fixture["task_render"]),
        "metric_spec": MetricSpec.model_validate(
            fixture["metric_spec"]
            | {
                "scoreability": PresenceScoreabilityContract.model_validate(
                    fixture["metric_spec"]["scoreability"]
                )
            }
        ),
        "planner_strategy": profile,
        "memory_history": [record],
    }
    bridge = _CaptureBridge()
    bridge.plan(**arguments)
    assert len(bridge.captures) == 1
    return bridge.captures[0]


def _historical_record(session):
    original = next(
        row for row in ORIGINAL["cases"] if row["case_id"] == session["case_id"]
    )
    record = deepcopy(_record(session))
    record["runtime_verification"]["runtime_policy"] = deepcopy(
        ORIGINAL["policies"][original["policy_index"]]
    )
    return record


def _profile_prefix(session):
    case = next(row for row in TRACES["cases"] if row["case_id"] == session["case_id"])
    late = case["reference_infra_revision"].startswith("349b6cd6")
    return "legacy-9b78d505cb11-paper" + ("-late" if late else "")


def test_actual_sessions_preserve_original_components_and_admission(sessions):
    originals = {row["case_id"]: row for row in ORIGINAL["cases"]}
    cases = {row["case_id"]: row for row in TRACES["cases"]}
    assert len(sessions) == len(originals) == 23
    for session in sessions:
        component_bytes = json.dumps(
            session["component"], sort_keys=True, separators=(",", ":")
        ).encode()
        assert (
            hashlib.sha256(component_bytes).hexdigest()
            == originals[session["case_id"]]["component_sha256"]
        )
        assert (
            session["admission"]
            == cases[session["case_id"]]["expected_archived"]["admission"]
        )


def test_v8_synthetic_era_policy_preserves_original_planner_requests(sessions):
    """Frozen policy plus verifier provenance isolates the v8-owned change.

    This synthetic carrier is not a current session or a recovered conversation.
    The current session is checked separately through the complete v11 chain.
    """
    for session in sessions:
        historical = _historical_record(session)
        incoming = deepcopy(historical)
        incoming["runtime_verification"]["runtime_policy"].update(
            {
                field: deepcopy(session["policy"][field])
                for field in (
                    "runtime_completion_policy",
                    "runtime_verifier",
                    "runtime_verifier_identity",
                )
            }
        )
        untouched = deepcopy(incoming)
        prefix = _profile_prefix(session)
        expected = _request(prefix + "-storage-v7", historical)
        assert _request(prefix + "-verifier-v8", incoming) == expected
        assert _request(prefix + "-storage-v7", incoming) != expected
        assert project_record(incoming) == historical
        assert incoming == untouched


def test_current_sessions_match_frozen_requests_through_v11(sessions):
    from agent.skills.check_config_format_skill.wrapper import run_skill

    manual = run_skill(None)["data"]
    before_manual = deepcopy(manual)
    for session in sessions:
        current = _record(session)
        untouched = deepcopy(current)
        prefix = _profile_prefix(session)
        expected = _request(prefix + "-storage-v7", _historical_record(session))
        assert (
            _request(prefix + "-scheduler-off-v11", current, config_manual=manual)
            == expected
        )
        # v8 does not own the later watchdog projection: it must retain that evidence.
        assert _request(prefix + "-verifier-v8", current) != expected
        assert current == untouched
    assert manual == before_manual


@pytest.mark.parametrize(
    "defect",
    [
        "partial",
        "native",
        "unknown",
        "changed",
        "selection",
        "completion_rule",
        "forecast",
        "completion_evidence",
        "future_policy",
        "components_shape",
    ],
)
def test_unqualified_new_record_is_not_silently_rewritten(sessions, defect):
    record = deepcopy(_record(sessions[0]))
    verification = record["runtime_verification"]
    policy = verification["runtime_policy"]
    if defect == "partial":
        policy.pop("runtime_verifier_identity")
    elif defect == "native":
        policy["runtime_verifier"] = None
        policy["runtime_verifier_identity"] = None
    elif defect == "unknown":
        policy["runtime_verifier_identity"]["name"] = "unknown"
    elif defect == "changed":
        policy["runtime_verifier_identity"]["content_sha256"] = "0" * 64
    elif defect == "selection":
        policy["runtime_verifier"] = "legacy-345c802d-verifier-v1"
    elif defect == "completion_rule":
        policy["runtime_completion_policy"] = "completed-workload-v1"
    elif defect == "forecast":
        policy["time_admission_source"] = "forecast"
    elif defect == "completion_evidence":
        verification["components"]["training"]["completion"] = {"completed": True}
    elif defect == "future_policy":
        policy["unqualified_behavior"] = True
    elif defect == "components_shape":
        verification["components"] = []
    untouched = deepcopy(record)
    with pytest.raises((TypeError, ValueError)):
        project_record(record)
    assert record == untouched


def test_archived_records_and_original_capture_driver_are_unchanged():
    record = {
        "status": "success",
        "runtime_verification": {"runtime_policy": ORIGINAL["policies"][0]},
    }
    assert project_record(record) == record
    assert (
        hashlib.sha256((ROOT / "replay.py").read_bytes()).hexdigest()
        == ORIGINAL["driver_sha256"]
    )


def test_runtime_package_is_required_only_for_the_explicit_new_profile(
    monkeypatch, sessions
):
    from agent.planner_strategy import resolve_planner_strategy

    original_import = builtins.__import__

    def without_runtime(name, *args, **kwargs):
        if name == "siderius_runtime_compat":
            raise ModuleNotFoundError(name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_runtime)
    assert resolve_planner_strategy("legacy-9b78d505cb11-paper-storage-v7") is not None
    with pytest.raises(ValueError, match="requires the installed"):
        resolve_planner_strategy("legacy-9b78d505cb11-paper-verifier-v8")
    with pytest.raises(ValueError, match="requires the installed"):
        project_record(_record(sessions[0]))
