"""Public TIDMAD row declaration for the orchestration validation client.

No data files are opened. This is a workload declaration, not authorization or
proof that the files exist: the private service must independently admit the
scope and require exact materialization using the unchanged task adapter.
"""

from execute_tools.dataset_config import resolve_dataset_profile
from execute_tools.task_data_path import (
    resolve_bound_task_data_path,
    resolve_task_scope_capability,
)

from tasks.tidmad.runtime.profile import tidmad_topology
from tasks.tidmad.runtime.tidmad_data_path import TidmadTaskDataPath


def declared_rows(scope: object) -> int:
    """Count declared ML windows using the task's canonical scope transport.

    File-loaded task plugins can have a different Python class identity than
    ordinary imports. Round-trip through the task-owned wire contract instead
    of asserting that the incoming scope is our imported TidmadScope class.
    The frozen validation adapter's count is checked by a materialization parity
    test; its task package is not changed to install this deployment adapter.
    """
    capability = resolve_task_scope_capability(resolve_bound_task_data_path())
    local_scope = TidmadTaskDataPath().deserialize_scope(
        capability.serialize_scope(scope)
    )
    profile = local_scope.profile or resolve_dataset_profile()
    windows = (
        tidmad_topology(profile).dataset.psd_segment_length // local_scope.seg_size
    )
    rows = sum(len(segments) * windows for segments in local_scope.sample_set.values())
    if rows <= 0:
        raise ValueError("TIDMAD validation scope declares no ML rows")
    return rows
