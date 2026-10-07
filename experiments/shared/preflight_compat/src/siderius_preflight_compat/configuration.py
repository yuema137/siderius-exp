"""Build an explicit historical declaration without mutating source manifests."""

from copy import deepcopy

from . import SELECTION


def historical_task_composition(manifest: dict) -> dict:
    """Return a declaration copy for an external task package and new workspace.

    This helper performs no filesystem writes, history import or launch. The
    caller owns copying the complete task package and preserving relative
    resources. A conflicting explicit selection requires a deliberate edit.
    """
    from core.inference_preflight_policy import InferencePreflightPolicy

    copied = deepcopy(manifest)
    previous = copied.get("preflight_estimator")
    if previous is not None and previous != SELECTION:
        raise ValueError(
            f"Task already selects a different preflight estimator: {previous!r}"
        )
    copied["preflight_estimator"] = SELECTION
    policy = InferencePreflightPolicy.model_validate(
        copied.get("inference_preflight", {"mode": "static_only", "max_batches": 3}),
        strict=True,
    )
    if policy.mode != "static_only":
        raise ValueError(
            "Historical task composition requires inference_preflight.mode=static_only; "
            "the task already selects a conflicting inference policy"
        )
    copied["inference_preflight"] = policy.model_dump(mode="json")
    return copied
