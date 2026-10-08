"""Installed historical timing profiles; installation does not change defaults."""

import json
from functools import partial
from pathlib import Path

_ROOT = Path(__file__).parent
_FAMILIES = ("345c802d", "7689fd58", "349b6cd6")


def historical_identities():
    """Return the exact package-owned identities for the qualified infra assembly."""
    return tuple(_historical_profile(family).identity() for family in _FAMILIES)


def require_historical_identity(identity):
    """Validate historical provenance without trusting a caller's provider name."""
    from core.runtime_control.verifier_provider import RuntimeVerifierIdentity

    parsed = RuntimeVerifierIdentity.model_validate(identity)
    if parsed not in historical_identities():
        raise ValueError(
            "Runtime verifier identity is not an exact qualified historical profile"
        )
    return parsed


def _historical_profile(family):
    from core.runtime_control.verifier_provider import RuntimeVerifierProfile

    from .adapter import create_historical_verifier

    qualification = json.loads((_ROOT / "qualification.json").read_text())
    sources = {
        name: _ROOT / name
        for name in (
            "__init__.py",
            "adapter.py",
            "adaptive_345c802d.py",
            "adaptive_7689fd58.py",
            "adaptive_349b6cd6.py",
            "steady_state.py",
            "source-inventory.json",
            "qualification.json",
        )
    }
    return RuntimeVerifierProfile(
        name=f"legacy-{family}-verifier-v1",
        version="1",
        create=partial(create_historical_verifier, family),
        sources=sources,
        qualified_assemblies=frozenset(
            row["assembly_sha256"] for row in qualification["assemblies"]
        ),
    )


def historical_345c802d():
    """Original TIDMAD verification without the later fast-suffix branch."""
    return _historical_profile("345c802d")


def historical_7689fd58():
    """Original TESS, LIGO and TIDMAD analysis-on fast-suffix verification."""
    return _historical_profile("7689fd58")


def historical_349b6cd6():
    """Original Project8 verification with active-interval accounting."""
    return _historical_profile("349b6cd6")
