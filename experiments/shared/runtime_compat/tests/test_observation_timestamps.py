"""Original clock semantics must survive populated historical prior consumption."""

import importlib
import json
import time
from datetime import datetime
from pathlib import Path

import pytest
from core.runtime_control.observation_store import (
    ObservationStore,
    calibration_key,
    observation_calibration_key,
)
from core.runtime_control.records import (
    PhaseComponentRecord,
    PhaseMeasurement,
    RuntimeObservation,
)
from core.runtime_control.session import (
    RuntimeControlPolicy,
    RuntimeVerificationSession,
)
from core.runtime_control.verifier_provider import resolve_runtime_verifier
from core.runtime_control.workload import ResolvedPhaseWorkload
from siderius_runtime_compat.observation_time import historical_timestamp_seconds

FIXTURE = json.loads(
    (
        Path(__file__).resolve().parents[1] / "fixtures/observation-timestamps.json"
    ).read_text()
)
CONTEXT = {
    "precision": "float32",
    "optimizer_type": "adamw",
    "model_family": "synthetic",
    "param_count": 32,
    "seg_size": 8,
    "batch_size": 2,
}


@pytest.fixture(params=["UTC", "America/Los_Angeles", "Asia/Shanghai"])
def timezone(request, monkeypatch):
    if not hasattr(time, "tzset"):
        pytest.skip("Host does not expose process timezone selection")
    with monkeypatch.context() as local:
        local.setenv("TZ", request.param)
        time.tzset()
        try:
            yield request.param
        finally:
            local.undo()
            time.tzset()


@pytest.mark.parametrize(
    "reference", FIXTURE["references"], ids=lambda r: r["revision"][:8]
)
def test_historical_parser_matches_original_source(reference, timezone):
    expected = next(r for r in reference["cases"] if r["timezone"] == timezone)
    assert [historical_timestamp_seconds(t) for t in FIXTURE["timestamps"]] == expected[
        "epoch_seconds"
    ]


def observation(identity, timestamp):
    return RuntimeObservation(
        timestamp=timestamp,
        hardware={"gpu_name": "synthetic"},
        software={"torch_version": "2.6.0"},
        runtime_policy={"runtime_verifier_identity": identity.model_dump(mode="json")},
        calibration_context=CONTEXT,
        components={
            "training": PhaseComponentRecord(
                workload=ResolvedPhaseWorkload(
                    phase="training", unit="optimizer_step", unit_count=10
                ),
                measurement=PhaseMeasurement(
                    unit="optimizer_step",
                    n_measured_units=10,
                    n_stabilization_units=0,
                    unit_time_ms_median=40,
                    steady_state_reached=True,
                    total_measurement_seconds=0.4,
                ),
            )
        },
        final_status="completed",
    )


@pytest.mark.parametrize(
    "reference", FIXTURE["references"], ids=lambda r: r["revision"][:8]
)
@pytest.mark.parametrize("boundary_hours", [-1, 0, 1])
def test_populated_store_and_session_preserve_old_expiry(
    reference, timezone, boundary_hours, tmp_path, monkeypatch
):
    selection = "legacy-" + reference["revision"][:8] + "-verifier-v1"
    profile = resolve_runtime_verifier(selection)
    identity = profile.identity()
    timestamp = FIXTURE["timestamps"][0]
    original_epoch = next(r for r in reference["cases"] if r["timezone"] == timezone)[
        "epoch_seconds"
    ][0]
    corrected_epoch = datetime.fromisoformat(timestamp).timestamp()
    now = corrected_epoch + 90 * 86400 + boundary_hours * 3600
    expected = "stale" if now - original_epoch > 90 * 86400 else "valid"
    store = ObservationStore(str(tmp_path / "store"))
    stored = observation(identity, timestamp)
    store.append(stored, writer_id="reference")
    key = observation_calibration_key(stored, "training")
    lookup = store.lookup_prior(
        key, "training", now=now, timestamp_parser=profile.observation_timestamp_parser
    )
    assert lookup.status == expected
    assert lookup.prior_unit_ms == 40
    native = store.lookup_prior(key, "training", now=now)
    assert native.status == ("stale" if boundary_hours > 0 else "valid")

    import core.runtime_control.session as session_owner

    monkeypatch.setattr(
        session_owner,
        "capture_environment_provenance",
        lambda: {"gpu_name": "synthetic", "torch_version": "2.6.0"},
    )
    monkeypatch.setattr(time, "time", lambda: now)
    session = RuntimeVerificationSession(
        str(tmp_path / "runtime.json"),
        policy=RuntimeControlPolicy(
            runtime_verifier=selection,
            runtime_completion_policy="verified-prediction-v1",
            observation_store_root=str(tmp_path / "store"),
        ),
    )
    session.set_calibration_context(CONTEXT)
    prior = session.lookup_phase_prior("training")
    expected_prior = 40 if expected == "valid" else None
    assert prior == expected_prior
    assert_frozen_verifier_flow(session, reference, prior, expected_prior, monkeypatch)

    # The time-wrapper's existing bare key cannot reuse provider-labelled rows.
    # Do not introduce a new historical preflight reuse path while fixing age.
    bare_key = calibration_key(
        "training", gpu_name="synthetic", torch_version="2.6.0", **CONTEXT
    )
    assert store.lookup_prior(bare_key, "training", now=now).status == "absent"


def assert_frozen_verifier_flow(session, reference, prior, expected_prior, monkeypatch):
    """Compare the consumed prior against the original frozen algorithm directly."""
    family = reference["revision"][:8]
    original = importlib.import_module("siderius_runtime_compat.adaptive_" + family)
    fields = session.policy.verification.model_dump(mode="json")
    if family == "345c802d":
        fields.pop("fast_phase_min_observations")
    monkeypatch.setattr(time, "perf_counter", lambda: 0.0)
    oracle = original.AdaptiveUnitVerification(
        "optimizer_step", original.AdaptiveVerificationConfig(**fields), expected_prior
    )
    actual = session.start_phase_verification(
        "training", "optimizer_step", prior_expected_unit_ms=prior
    )
    for _ in range(300):
        if actual.is_terminal or oracle.is_terminal:
            break
        assert actual.feed(40, elapsed_ms=40) == oracle.feed(40, elapsed_ms=40)
    assert actual.finalize() == oracle.finalize() == "verified"
    assert actual.measurement().model_dump(
        mode="json"
    ) == oracle.measurement().model_dump(mode="json")
    workload = ResolvedPhaseWorkload(
        phase="training", unit="optimizer_step", unit_count=1000
    )
    assert actual.prediction(workload, "real_training_verification").model_dump(
        mode="json"
    ) == oracle.prediction(workload, "real_training_verification").model_dump(
        mode="json"
    )
