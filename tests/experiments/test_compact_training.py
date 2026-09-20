"""Catch original-vs-packed segment confusion with actual task data loading."""

import json
from pathlib import Path

import h5py
import numpy as np
import pytest
from execute_tools.dataset_config import DatasetProfile
from execute_tools.task_data_path import EpochSamplingParams, EvalMaterializationParams
from execute_tools.task_registration_scope import run_registration_scope

from experiments.tidmad.main_orchestrator.compact_training import (
    CompactFrozenPoolDataPath,
)
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope, TidmadTaskDataPath

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def registration_scope():
    with run_registration_scope():
        yield


@pytest.fixture
def packed(tmp_path):
    manifest = ROOT / "tasks/tidmad/declared/frozen_training_pool_v1.json"
    pool = json.loads(manifest.read_text())
    originals = pool["sample_set"]["0"]
    length = pool["psd_segment_length"]
    path = tmp_path / "abra_training_0000.h5"
    with h5py.File(path, "w") as file:
        for channel, delta in (("channel0001", 0), ("channel0002", 2)):
            data = file.create_dataset(
                f"timeseries/{channel}/timeseries",
                shape=(len(originals) * length,),
                dtype="int8",
                chunks=(40000,),
            )
            data[:40000] = 21 + delta
            data[
                (len(originals) - 1) * length : (len(originals) - 1) * length + 40000
            ] = 43 + delta
    profile = DatasetProfile.model_validate_json(
        (ROOT / "tasks/tidmad/resolved/dataset_profile.json").read_text()
    )
    scope = TidmadScope(
        sample_set={0: [originals[-1], originals[0]]}, seg_size=40000, profile=profile
    )
    adapter = CompactFrozenPoolDataPath(
        frozen_manifest=str(
            ROOT / "tasks/tidmad/compositions/continuous_regression_frozen_pool.yaml"
        )
    )
    scope = adapter.deserialize_scope(TidmadTaskDataPath().serialize_scope(scope))
    return (
        adapter,
        scope,
        path,
        originals,
        length,
    )


def test_training_reads_compact_positions_preserving_original_scope(packed, tmp_path):
    adapter, scope, path, originals, length = packed
    before = adapter.serialize_scope(scope)
    data = adapter.training_dataset(
        scope, EpochSamplingParams(data_dir=str(tmp_path), max_samples=251)
    )
    assert len(data) == 251
    np.testing.assert_array_equal(data[0][0], np.full(40000, 43 + 128))
    np.testing.assert_array_equal(data[0][1], np.full(40000, 45 + 128))
    np.testing.assert_array_equal(data[250][0], np.full(40000, 21 + 128))
    assert adapter.serialize_scope(scope) == before
    physical = adapter.storage_read_scope(str(tmp_path), scope)
    assert physical.expected_on_disk_bytes == round(
        path.stat().st_size * 2 / len(originals)
    )
    # Validation remains in original coordinates, even when an original ID is
    # much larger than the number of compact training positions.
    with h5py.File(tmp_path / "abra_validation_0000.h5", "w") as file:
        for channel in ("channel0001", "channel0002"):
            data = file.create_dataset(
                f"timeseries/{channel}/timeseries",
                shape=(200 * length,),
                dtype="int8",
                chunks=(40000,),
            )
            data[originals[-1] * length : originals[-1] * length + 40000] = 61
    validation = adapter.validation_dataset(
        scope, EvalMaterializationParams(data_dir=str(tmp_path))
    )
    np.testing.assert_array_equal(validation[0][0], np.full(40000, 61 + 128))


def test_wrong_physical_layout_and_out_of_pool_selection_are_refused(packed, tmp_path):
    adapter, scope, path, originals, _ = packed
    outside = next(index for index in range(200) if index not in originals)
    with pytest.raises(ValueError, match="outside the frozen pool"):
        adapter.training_dataset(
            scope.model_copy(update={"sample_set": {0: [outside]}}),
            EpochSamplingParams(data_dir=str(tmp_path)),
        )
    with h5py.File(path, "a") as file:
        del file["timeseries/channel0002/timeseries"]
        file.create_dataset(
            "timeseries/channel0002/timeseries", shape=(1,), dtype="int8"
        )
    with pytest.raises(ValueError, match="compact frozen layout"):
        adapter.training_dataset(scope, EpochSamplingParams(data_dir=str(tmp_path)))
