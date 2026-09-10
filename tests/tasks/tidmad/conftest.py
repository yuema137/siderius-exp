"""Task-owned fixtures for TIDMAD runtime witnesses."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest
from execute_tools.dataset_config import DatasetProfile, bind_dataset_profile


@pytest.fixture
def tidmad_profile():
    """Read this task's declaration; never rely on a framework default."""
    root = Path(__file__).resolve().parents[3]
    declaration = root / "tasks/tidmad/resolved/dataset_profile.json"
    return DatasetProfile.model_validate_json(declaration.read_text())


@pytest.fixture
def bound_tidmad_profile(tidmad_profile):
    """Opt-in binding, restored after each task-owned witness."""
    with bind_dataset_profile(tidmad_profile):
        yield tidmad_profile


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
