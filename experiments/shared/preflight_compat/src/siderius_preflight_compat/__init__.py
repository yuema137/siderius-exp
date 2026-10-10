"""Explicit, source-pinned historical estimation; installation changes no default."""

import json
from pathlib import Path

SELECTION = "legacy-078b23ca-preflight-v1"
_ROOT = Path(__file__).parent


def source_files() -> dict[str, Path]:
    """Sources controlling arithmetic and historical projection eligibility."""
    return {
        name: _ROOT / name
        for name in (
            "__init__.py",
            "arithmetic.py",
            "configuration.py",
            "provenance.json",
            "qualification.json",
        )
    }


def historical_profile():
    import core.preflight_estimation as registry

    from .arithmetic import estimate_historical_phase

    qualification = json.loads((_ROOT / "qualification.json").read_text())
    assemblies = frozenset(
        row["assembly_sha256"] for row in qualification["assemblies"]
    )
    # Qualified older frameworks enforce this rule internally and lack the field.
    # New frameworks require the historical provider to declare it explicitly.
    policy = {}
    if "workload_rule" in registry.PreflightEstimatorProfile.__dataclass_fields__:
        policy["workload_rule"] = registry.BatchSegmentationLimit(limit=800000)
    return registry.PreflightEstimatorProfile(
        name=SELECTION,
        version="1",
        estimate=estimate_historical_phase,
        sources=source_files(),
        qualified_assemblies=assemblies,
        **policy,
    )


def require_historical_identity(identity) -> None:
    """Permit projection only for exact source-qualified historical arithmetic.

    The running framework must itself be qualified. An earlier qualified
    assembly can appear in a read-only record only with the same provider
    implementation fingerprint. Unknown package/source identities fail closed.
    """
    from core.preflight_estimation import PreflightEstimatorIdentity

    actual = PreflightEstimatorIdentity.model_validate(identity)
    profile = historical_profile()
    expected = profile.identity()
    if actual.assembly_sha256 not in profile.qualified_assemblies:
        raise ValueError(
            "Historical preflight record uses an unqualified estimation assembly"
        )
    expected = expected.model_copy(update={"assembly_sha256": actual.assembly_sha256})
    if actual != expected:
        raise ValueError(
            "Historical preflight projection requires the exact qualified estimator identity"
        )
