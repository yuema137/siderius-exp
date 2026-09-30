"""Public row declaration for the orchestration validation client.

No data file is opened. This declares a workload — how many rows the caller
says it wants evaluated — and is neither authorization nor evidence that the
curves exist. The evaluator admits the scope separately
(`validation_scope.admit_validation_scope`) and materializes it through the
unchanged task adapter.

**Why the round trip.** A file-loaded task plugin can have a different
Python class identity from the same class imported normally, so asserting
`isinstance(scope, TessScope)` on what arrives is unreliable. TIDMAD's
equivalent records the same reason. The scope is therefore re-read through
the task-owned wire contract rather than trusted as an object.
"""

from __future__ import annotations

import json

from execute_tools.task_data_path import (
    resolve_bound_task_data_path,
    resolve_task_scope_capability,
)

from tasks.phyts_tess.runtime.tess_data_path import TessScope

__all__ = ["declared_rows"]


def declared_rows(scope: object) -> int:
    """Count the curves a validation scope declares.

    One curve is one row: TESS evaluates a fixed-length window per light
    curve, so there is no windows-per-file factor of the kind TIDMAD's
    segmentation introduces.

    The payload is re-validated with the pack's own scope model rather than
    through `PhytsTessTaskDataPath.deserialize_scope`, because that adapter's
    constructor requires a manifest path — and a row *declaration* must not
    need to open the population it is counting against.
    """
    capability = resolve_task_scope_capability(resolve_bound_task_data_path())
    payload = json.loads(capability.serialize_scope(scope))
    if set(payload) != {"kind", "scope"}:
        raise ValueError("validation scope payload is not the task's wire form")

    rows = len(TessScope.model_validate(payload["scope"]).rows)
    if rows <= 0:
        raise ValueError("PhyTS TESS validation scope declares no rows")
    return rows
