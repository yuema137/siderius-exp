"""Task-owned fixtures for TIDMAD runtime witnesses."""

from __future__ import annotations

import h5py
import numpy as np
import pytest


@pytest.fixture
def synthetic_h5(tmp_path):
    """Create the smallest TIDMAD-shaped training file for a requested segment."""

    def _make(seg_size: int) -> tuple[str, str]:
        filename = "abra_training_0000.h5"
        path = tmp_path / filename
        rng = np.random.default_rng(42)
        with h5py.File(path, "w") as handle:
            timeseries = handle.create_group("timeseries")
            timeseries.create_group("channel0001").create_dataset(
                "timeseries",
                data=rng.integers(-128, 127, size=seg_size, dtype=np.int8),
            )
            timeseries.create_group("channel0002").create_dataset(
                "timeseries",
                data=rng.integers(-128, 127, size=seg_size, dtype=np.int16),
            )
        return str(tmp_path), filename

    return _make
