"""Original-source oracles for explicitly selected installed historical verifiers."""

import hashlib
import json
from pathlib import Path

import pytest
import siderius_runtime_compat
from core.runtime_control.adaptive import AdaptiveVerificationConfig
from core.runtime_control.workload import ResolvedPhaseWorkload
from siderius_runtime_compat.adapter import create_historical_verifier

from experiments.shared.runtime_compat.trace_replay import drive_trace

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "fixtures/paper-finite-workloads.json").read_text())["cases"]
BRANCH_INPUT = json.loads((ROOT / "fixtures/version-branches-input.json").read_text())
BRANCHES = [
    (family, case, expected)
    for family in ("345c802d", "7689fd58", "349b6cd6")
    for case, expected in zip(
        BRANCH_INPUT["cases"],
        json.loads((ROOT / f"fixtures/branches-{family}.json").read_text())["results"],
        strict=True,
    )
]


def create(family, config, prior=None):
    return create_historical_verifier(
        family,
        unit="optimizer_step",
        config=AdaptiveVerificationConfig.model_validate(config),
        prior_expected_unit_ms=prior,
        completion_policy="verified-prediction-v1",
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case_id"])
def test_installed_verifier_preserves_original_archive_measurement(case):
    inputs = case["input"]
    verifier = create(
        case["reference_infra_revision"][:8],
        inputs["verification"],
        inputs["prior_expected_unit_ms"],
    )
    for rate, elapsed in zip(
        inputs["unit_timings_ms"], inputs["observation_elapsed_ms"], strict=True
    ):
        verifier.feed(rate, elapsed_ms=elapsed)
    assert verifier.finalize() == "failed_no_steady_state"
    assert (
        verifier.measurement().model_dump(mode="json")
        == case["expected_archived"]["measurement"]
    )
    assert verifier.permits_workload_completion is False


@pytest.mark.parametrize(
    ("family", "case", "expected"),
    BRANCHES,
    ids=[f"{family}:{case['case_id']}" for family, case, _ in BRANCHES],
)
def test_version_branches_match_original_reference_outputs(family, case, expected):
    verifier = create(family, case["config"])
    observed = drive_trace(verifier, case["segments"])
    assert observed == expected["observed_units"]
    assert verifier.state == expected["state"]
    assert verifier.measurement().model_dump(mode="json") == expected["measurement"]
    if verifier.state == "verified":
        workload = ResolvedPhaseWorkload(
            phase="training",
            unit="optimizer_step",
            unit_count=sum(len(segment["rates_ms"]) for segment in case["segments"]),
        )
        assert (
            verifier.prediction(workload, "real_dataset_warmup").model_dump(mode="json")
            == expected["prediction"]
        )
    else:
        assert expected["prediction"] is None


@pytest.mark.parametrize("family", ["345c802d", "7689fd58", "349b6cd6"])
def test_historical_verifier_refuses_corrected_completion_rule(family):
    with pytest.raises(ValueError, match="require runtime_completion_policy"):
        create_historical_verifier(
            family,
            unit="optimizer_step",
            config=AdaptiveVerificationConfig(),
            prior_expected_unit_ms=None,
            completion_policy="completed-workload-v1",
        )


def test_no_fast_suffix_profile_refuses_a_conflicting_new_setting():
    with pytest.raises(ValueError, match="nondefault fast_phase_min_observations"):
        create("345c802d", {"fast_phase_min_observations": 50})


def test_installed_frozen_sources_match_declared_inventory():
    package = Path(siderius_runtime_compat.__file__).parent
    for row in json.loads((package / "source-inventory.json").read_text()):
        data = (package / row["packaged_file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["packaged_sha256"]
        if row["only_change"] is not None:
            change = row["only_change"]
            assert data.count(change["to"].encode()) == 1
            data = data.replace(change["to"].encode(), change["from"].encode())
        assert hashlib.sha256(data).hexdigest() == row["source_sha256"]


def test_reference_capture_inputs_and_driver_have_not_drifted():
    for family in ("345c802d", "7689fd58", "349b6cd6"):
        receipt = json.loads((ROOT / f"fixtures/branches-{family}.json").read_text())
        for relative, key in (
            ("fixtures/version-branches-input.json", "fixture_sha256"),
            ("capture_reference.py", "capture_sha256"),
            ("trace_replay.py", "trace_driver_sha256"),
        ):
            assert (
                hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
                == receipt[key]
            )
