"""Build an explicit historical declaration without mutating source manifests."""

from copy import deepcopy

from . import SELECTION


def historical_task_composition(manifest: dict) -> dict:
    """Return a declaration copy for an external task package and new workspace.

    This helper performs no filesystem writes, history import or launch. The
    caller owns copying the complete task package and preserving relative
    resources. A conflicting explicit selection requires a deliberate edit.
    """
    copied = deepcopy(manifest)
    previous = copied.get("preflight_estimator")
    if previous is not None and previous != SELECTION:
        raise ValueError(
            f"Task already selects a different preflight estimator: {previous!r}"
        )
    copied["preflight_estimator"] = SELECTION
    return copied
