"""Task-owned half of the historical Step-07a exact-validation regressions.

The generic trainer tests cover propagation and no-success-artifact behavior.
These witnesses exercise the actual external HDF5 adapter: missing or truncated
data, empty selection, per-file identity and data changing between passes.
"""

from pathlib import Path

import h5py
import numpy as np
import pytest
from execute_tools.dataset_config import DatasetProfile
from execute_tools.task_data_path import (
    EpochSamplingParams,
    EvalMaterializationParams,
    ValidationScopeError,
)

from tasks.tidmad.runtime import tidmad_data_path as data_path
from tasks.tidmad.runtime.profile import tidmad_topology

TASK_ROOT = Path(__file__).resolve().parents[3] / "tasks" / "tidmad"
ROW_LENGTH = 8
SEGMENT_LENGTH = 16
SEGMENTS_PER_FILE = 2


@pytest.fixture
def fixture_data(tmp_path):
    profile = DatasetProfile.model_validate_json(
        (TASK_ROOT / "resolved" / "dataset_profile.json").read_text()
    )
    payload = profile.to_wire()
    payload["dataset"].update(
        num_files=2,
        psd_segment_length=SEGMENT_LENGTH,
        segments_per_file=SEGMENTS_PER_FILE,
    )
    payload["anchor_selection_files"] = [0, 1]
    payload["health_peek_files"] = [0, 1]
    profile = DatasetProfile.model_validate(payload)
    topology = tidmad_topology(profile)
    for family in ("training", "validation"):
        for index in range(2):
            name = getattr(topology.dataset, f"{family}_file_name")(index)
            with h5py.File(tmp_path / name, "w") as handle:
                for channel in (
                    topology.channels.input_channel,
                    topology.channels.target_channel,
                ):
                    values = np.arange(
                        SEGMENT_LENGTH * SEGMENTS_PER_FILE, dtype=np.int8
                    )
                    values += index + (10 if family == "validation" else 0)
                    handle.create_dataset(
                        f"timeseries/{channel}/timeseries", data=values
                    )
    scope = data_path.TidmadScope(
        sample_set={"0": [0, 1], "1": [0, 1]}, seg_size=ROW_LENGTH, profile=profile
    )
    return tmp_path, profile, scope


def _materialize(root, scope):
    return data_path.TidmadTaskDataPath().validation_dataset(
        scope, EvalMaterializationParams(data_dir=str(root))
    )


def test_full_scope_preserves_per_file_counts_and_uses_validation_family(fixture_data):
    root, _profile, scope = fixture_data
    validation = _materialize(root, scope)
    training = data_path.TidmadTaskDataPath().training_dataset(
        scope, EpochSamplingParams(data_dir=str(root), epoch_seed=7)
    )
    assert len(validation) == len(training) == 8
    assert validation.file_row_ranges == {0: (0, 4), 1: (4, 8)}
    assert np.array_equal(validation[0][0] - training[0][0], np.full(ROW_LENGTH, 10))


def test_validation_construction_reads_metadata_not_signal_arrays(
    fixture_data, monkeypatch
):
    """A full Formal scope must not be copied into host RAM at construction.

    The pre-fix adapter sliced both channels for every selected PSD segment
    inside ``__init__``. Reintroducing that eager read makes ``reads`` nonzero
    before the first DataLoader item is requested.
    """
    root, _profile, scope = fixture_data
    real_h5_dataset = data_path._h5_dataset
    reads: list[object] = []

    class _TrackedDataset:
        def __init__(self, wrapped):
            self._wrapped = wrapped

        def __len__(self):
            return len(self._wrapped)

        def __getitem__(self, key):
            reads.append(key)
            return self._wrapped[key]

    def tracked_h5_dataset(handle, *path):
        return _TrackedDataset(real_h5_dataset(handle, *path))

    monkeypatch.setattr(data_path, "_h5_dataset", tracked_h5_dataset)
    validation = _materialize(root, scope)
    assert reads == []

    validation[0]
    assert len(reads) == 2


def test_bounded_target_materialization_preserves_storage_values(fixture_data):
    """The streamed deliverable writer can recover targets without a full copy."""
    root, profile, scope = fixture_data
    validation = _materialize(root, scope)

    stored = validation.materialize_storage_targets(1, 7)
    expected = (
        np.stack([validation[index][1] for index in range(1, 7)])
        - tidmad_topology(profile).encoding.value_offset
    )

    assert stored.dtype == np.dtype(tidmad_topology(profile).encoding.storage_dtype)
    assert np.array_equal(stored, expected)


@pytest.mark.parametrize("selection", [{"0": [0, 1], "1": [0, 1]}, {"7": [0]}])
def test_missing_validation_file_or_foreign_partition_refuses(fixture_data, selection):
    root, profile, scope = fixture_data
    (root / tidmad_topology(profile).dataset.validation_file_name(1)).unlink()
    requested = scope.model_copy(update={"sample_set": selection})
    with pytest.raises(ValidationScopeError, match="materialized .* requested"):
        _materialize(root, requested)
    # Historical asymmetry: missing training files may be skipped, but that
    # tolerance must not shrink a validation identity scope silently.
    (root / tidmad_topology(profile).dataset.training_file_name(1)).unlink()
    training = data_path.TidmadTaskDataPath().training_dataset(
        scope, EpochSamplingParams(data_dir=str(root), epoch_seed=7)
    )
    assert len(training) == 4


def test_segment_beyond_physical_file_cannot_produce_validation_rows(fixture_data):
    root, _profile, scope = fixture_data
    requested = scope.model_copy(update={"sample_set": {"0": [SEGMENTS_PER_FILE]}})
    with pytest.raises(ValidationScopeError, match="holds only 2 complete PSD segment"):
        _materialize(root, requested)


def test_empty_validation_scope_is_refused_instead_of_reaching_r3_division(
    fixture_data,
):
    root, _profile, scope = fixture_data
    requested = scope.model_copy(update={"sample_set": {"0": []}})
    with pytest.raises(ValidationScopeError):
        _materialize(root, requested)


def test_data_disappearing_between_passes_cannot_shrink_the_next_pass(fixture_data):
    root, profile, scope = fixture_data
    assert len(_materialize(root, scope)) == 8
    (root / tidmad_topology(profile).dataset.validation_file_name(1)).unlink()
    with pytest.raises(
        ValidationScopeError, match="materialized 4 ML rows.*8 were requested"
    ):
        _materialize(root, scope)


def test_equal_total_does_not_hide_wrong_per_file_materialization(
    fixture_data, monkeypatch
):
    root, _profile, scope = fixture_data
    real_init = data_path.TIDMADValidationDataset.__init__

    def wrong_file_ranges(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        assert len(self) == 8  # Real HDF5 data and total remain intact.
        self.file_row_ranges = {0: (0, 3), 1: (3, 8)}

    monkeypatch.setattr(
        data_path.TIDMADValidationDataset, "__init__", wrong_file_ranges
    )
    with pytest.raises(
        ValidationScopeError, match="materialized 8 ML rows.*8 were requested"
    ):
        _materialize(root, scope)
