"""Installed historical timing profiles; installation does not change defaults."""

import json
from functools import partial
from pathlib import Path

_ROOT = Path(__file__).parent


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
