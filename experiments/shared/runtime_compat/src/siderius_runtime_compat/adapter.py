"""Adapt frozen verifier APIs without changing their numerical or clock rules."""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from typing import Any, Literal

from core.runtime_control.adaptive import AdaptiveVerificationConfig, VerificationState
from core.runtime_control.records import (
    PhaseMeasurement,
    PredictionSource,
    RuntimePrediction,
)
from core.runtime_control.workload import ResolvedPhaseWorkload

from . import adaptive_345c802d, adaptive_349b6cd6, adaptive_7689fd58

Family = Literal["345c802d", "7689fd58", "349b6cd6"]
FrozenVerifier = (
    adaptive_345c802d.AdaptiveUnitVerification
    | adaptive_7689fd58.AdaptiveUnitVerification
    | adaptive_349b6cd6.AdaptiveUnitVerification
)
_MODULES = {
    "345c802d": adaptive_345c802d,
    "7689fd58": adaptive_7689fd58,
    "349b6cd6": adaptive_349b6cd6,
}


class HistoricalVerifier:
    """Delegate the public phase-verification surface to one frozen implementation."""

    def __init__(self, verifier: FrozenVerifier):
        self._verifier = verifier

    @property
    def state(self) -> VerificationState:
        return self._verifier.state

    @property
    def is_terminal(self) -> bool:
        return self._verifier.is_terminal

    @property
    def verification_seconds(self) -> float:
        return self._verifier.verification_seconds

    @property
    def failure_reason(self) -> str | None:
        return self._verifier.failure_reason

    @property
    def permits_workload_completion(self) -> bool:
        return False

    def active_interval(self) -> AbstractContextManager[None]:
        if isinstance(self._verifier, adaptive_349b6cd6.AdaptiveUnitVerification):
            return self._verifier.active_interval()
        # These original versions measured wall time from their first feed;
        # excluding gaps would change their historical verification deadline.
        return nullcontext()

    def feed(
        self, unit_ms: float, *, elapsed_ms: float | None = None
    ) -> VerificationState:
        return self._verifier.feed(unit_ms, elapsed_ms=elapsed_ms)

    def finalize(self) -> VerificationState:
        return self._verifier.finalize()

    def measurement(self) -> PhaseMeasurement | None:
        return self._verifier.measurement()

    def prediction(
        self,
        workload: ResolvedPhaseWorkload,
        source: PredictionSource,
        *,
        safety_factor: float = 1.0,
        extra_predicted_seconds: float = 0.0,
        extra_detail: dict[str, Any] | None = None,
    ) -> RuntimePrediction:
        return self._verifier.prediction(
            workload,
            source,
            safety_factor=safety_factor,
            extra_predicted_seconds=extra_predicted_seconds,
            extra_detail=extra_detail,
        )


def create_historical_verifier(
    family: Family,
    *,
    unit: str,
    config: AdaptiveVerificationConfig,
    prior_expected_unit_ms: float | None,
    completion_policy: str,
) -> HistoricalVerifier:
    """Validate an explicit historical selection before creating the verifier."""
    if completion_policy != "verified-prediction-v1":
        raise ValueError(
            "Historical runtime verifiers require runtime_completion_policy="
            "verified-prediction-v1; use a fresh workspace with that explicit selection"
        )
    module = _MODULES[family]
    configuration = config.model_dump(mode="json")
    if family == "345c802d":
        # Native policy transport includes this later field. The old algorithm
        # had no fast-suffix branch; only the unchanged transported default is
        # accepted, and cannot enable that nonexistent branch.
        if configuration.get("fast_phase_min_observations") != 100:
            raise ValueError(
                "Verifier 345c802d does not support a nondefault "
                "fast_phase_min_observations setting"
            )
        configuration.pop("fast_phase_min_observations")
    unknown = (
        configuration.keys() - module.AdaptiveVerificationConfig.model_fields.keys()
    )
    if unknown:
        raise ValueError(
            f"Historical verifier does not support fields: {sorted(unknown)}"
        )
    frozen_config = module.AdaptiveVerificationConfig.model_validate(configuration)
    verifier = module.AdaptiveUnitVerification(
        unit, frozen_config, prior_expected_unit_ms
    )
    return HistoricalVerifier(verifier)
