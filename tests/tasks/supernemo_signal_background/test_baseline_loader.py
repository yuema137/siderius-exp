"""Regression tests for bounded SuperNEMO baseline data selection."""

from __future__ import annotations

import numpy as np

from tasks.supernemo_signal_background.tools.run_baseline import _local_selection


def test_global_balanced_selection_maps_to_each_process_without_drift() -> None:
    """A process boundary must neither drop nor steal a neighbouring event."""
    selected = np.array([0, 2, 4, 5, 8, 9, 12])

    first = _local_selection(selected, global_offset=0, process_count=5)
    second = _local_selection(selected, global_offset=5, process_count=5)
    third = _local_selection(selected, global_offset=10, process_count=5)

    np.testing.assert_array_equal(first, np.array([0, 2, 4]))
    np.testing.assert_array_equal(second, np.array([0, 3, 4]))
    np.testing.assert_array_equal(third, np.array([2]))
