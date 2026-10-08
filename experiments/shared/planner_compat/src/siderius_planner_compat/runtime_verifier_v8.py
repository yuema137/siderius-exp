"""Explicit historical display of source-qualified runtime verifier provenance."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from .storage_provenance_v7 import historical_storage_late_v7, historical_storage_v7

_NEW_POLICY_FIELDS = frozenset(
    {"runtime_completion_policy", "runtime_verifier", "runtime_verifier_identity"}
)


def _runtime_compat():
    try:
        import siderius_runtime_compat
    except ImportError as exc:
        raise ValueError(
            "Historical verifier presentation requires the installed "
            "siderius-runtime-compat package in this interpreter"
        ) from exc
    return siderius_runtime_compat


def project_record(record: dict[str, Any]) -> dict[str, Any]:
    """Remove only qualified additive identity fields from a rendering copy."""
    result = deepcopy(record)
    verification = result.get("runtime_verification")
    if verification is None:
        return result
    if not isinstance(verification, dict):
        raise TypeError(
            "Historical verifier projection requires a runtime_verification mapping"
        )
    policy = verification.get("runtime_policy")
    if policy is None:
        return result
    if not isinstance(policy, dict):
        raise TypeError(
            "Historical verifier projection requires a runtime_policy mapping"
        )
    if not _NEW_POLICY_FIELDS.intersection(policy):
        return result
    if not _NEW_POLICY_FIELDS.issubset(policy):
        raise ValueError(
            "Historical verifier projection requires complete verifier provenance"
        )
    if (
        policy["runtime_completion_policy"] != "verified-prediction-v1"
        or policy.get("time_admission_source") != "measured"
    ):
        raise ValueError(
            "Historical verifier projection requires strict measured admission"
        )

    from core.runtime_control.session import RuntimeControlPolicy

    if policy.keys() - RuntimeControlPolicy.model_fields.keys():
        raise ValueError(
            "Historical verifier projection encountered unknown runtime policy fields"
        )
    expected = _runtime_compat().require_historical_identity(
        policy["runtime_verifier_identity"]
    )
    if policy["runtime_verifier"] != expected.name:
        raise ValueError("Historical verifier selection contradicts its identity")
    # Re-resolve the installed provider; package-owned identity alone does not
    # establish that the currently registered entrypoint still matches it.
    RuntimeControlPolicy.model_validate(policy)
    components = verification.get("components", {})
    if not isinstance(components, dict):
        raise TypeError("Historical verifier projection requires a components mapping")
    for component in components.values():
        if not isinstance(component, dict):
            raise TypeError(
                "Historical verifier projection requires component mappings"
            )
        if component.get("completion") is not None:
            raise ValueError(
                "Historical verifier projection cannot hide completed-workload evidence"
            )
    for key in _NEW_POLICY_FIELDS:
        policy.pop(key)
    return result


def _provider(*, late: bool):
    from core.planner_strategy_identity import (
        PlannerStrategyIdentity,
        source_fingerprint,
    )

    original = historical_storage_late_v7() if late else historical_storage_v7()
    identities = _runtime_compat().historical_identities()
    sources = {
        "v7_identity.json": original.identity.model_dump_json().encode(),
        "runtime_verifier_v8.py": Path(__file__).read_bytes(),
    } | {identity.name: identity.model_dump_json().encode() for identity in identities}

    def render(*, memory_history, **arguments):
        return original.user_renderer(
            memory_history=[project_record(record) for record in memory_history],
            **arguments,
        )

    name = "legacy-9b78d505cb11-paper" + ("-late" if late else "") + "-verifier-v8"
    return replace(
        original,
        identity=PlannerStrategyIdentity(
            name=name, version="8", content_sha256=source_fingerprint(sources)
        ),
        user_renderer=render,
    )


def historical_verifier_v8():
    return _provider(late=False)


def historical_verifier_late_v8():
    return _provider(late=True)
