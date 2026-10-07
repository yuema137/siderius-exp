"""Task-owned half of the historical Step-07a exact-validation regressions.

The generic trainer tests cover propagation and no-success-artifact behavior.
These witnesses exercise the actual external HDF5 adapter: missing or truncated
data, empty selection, per-file identity and data changing between passes.
"""

from pathlib import Path

import h5py
import numpy as np
import pytest
from execute_tools.dataset_config import DatasetProfile, bind_dataset_profile
from execute_tools.task_data_path import (
    EpochSamplingParams,
    EvalMaterializationParams,
    HealthCoverageRequest,
    ScopeBuildRequest,
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
    real_read = data_path.HDF5ReadCache.read
    reads: list[object] = []

    def tracked_read(self, path, dataset, selection):
        reads.append(selection)
        return real_read(self, path, dataset, selection)

    monkeypatch.setattr(data_path.HDF5ReadCache, "read", tracked_read)
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
    with pytest.raises(ValidationScopeError, match=r"materialized .* requested"):
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


@pytest.mark.parametrize("selection", [{}, {"0": []}, {"0": [], "1": []}])
def test_empty_validation_scope_is_refused_instead_of_reaching_r3_division(
    fixture_data,
    selection,
):
    root, _profile, scope = fixture_data
    requested = scope.model_copy(update={"sample_set": selection})
    with pytest.raises(ValidationScopeError):
        _materialize(root, requested)


def test_data_disappearing_between_passes_cannot_shrink_the_next_pass(fixture_data):
    root, profile, scope = fixture_data
    assert len(_materialize(root, scope)) == 8
    (root / tidmad_topology(profile).dataset.validation_file_name(1)).unlink()
    with pytest.raises(
        ValidationScopeError,
        match=r"materialized 4 ML rows.*8 were requested",
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
        ValidationScopeError,
        match=r"materialized 8 ML rows.*8 were requested",
    ):
        _materialize(root, scope)


def test_compressed_discontinuous_rows_keep_encoding_order_and_pickle(fixture_data):
    """Reader integration must preserve task-selected rows, including reversed PSDs."""
    import pickle

    root, profile, scope = fixture_data
    topology = tidmad_topology(profile)
    for index in range(2):
        with h5py.File(
            root / topology.dataset.validation_file_name(index), "a"
        ) as handle:
            for channel in (
                topology.channels.input_channel,
                topology.channels.target_channel,
            ):
                name = f"timeseries/{channel}/timeseries"
                values = handle[name][:]
                del handle[name]
                handle.create_dataset(
                    name, data=values, chunks=(16,), compression="gzip"
                )
    scope = scope.model_copy(update={"sample_set": {"1": [1, 0], "0": [1]}})
    dataset = _materialize(root, scope)
    expected = [[], []]
    for index, segments in ((0, [1]), (1, [1, 0])):
        with h5py.File(root / topology.dataset.validation_file_name(index)) as handle:
            for output, channel in zip(
                expected,
                (topology.channels.input_channel, topology.channels.target_channel),
                strict=True,
            ):
                for segment in segments:
                    values = (
                        handle[f"timeseries/{channel}/timeseries"][
                            segment * SEGMENT_LENGTH : (segment + 1) * SEGMENT_LENGTH
                        ].astype(topology.encoding.compute_dtype)
                        + topology.encoding.value_offset
                    )
                    output.extend(values.reshape(-1, ROW_LENGTH))
    for index in range(len(dataset)):
        for channel in range(2):
            np.testing.assert_array_equal(
                dataset[index][channel], expected[channel][index]
            )
    restored = pickle.loads(pickle.dumps(dataset))
    np.testing.assert_array_equal(restored[-1][0], expected[0][-1])
    np.testing.assert_array_equal(dataset[-1][0], expected[0][-1])
    dataset.close()
    restored.close()


@pytest.mark.parametrize("segment_size, expected", [(4, 16), (8, 8), (16, 4)])
def test_orchestration_public_row_declaration_matches_materialization_without_io(
    fixture_data, monkeypatch, segment_size, expected
):
    """Wrong ML/PSD conversion fails parity; accidental private I/O raises."""
    from execute_tools.task_data_path import bind_task_data_path

    from experiments.tidmad.main_orchestrator.validation_rows import declared_rows

    root, _, scope = fixture_data
    scope = scope.model_copy(update={"seg_size": segment_size})
    materialized = len(_materialize(root, scope))

    def forbidden(*args, **kwargs):
        raise AssertionError("public row declaration attempted HDF5 access")

    monkeypatch.setattr(h5py, "File", forbidden)
    with bind_task_data_path(data_path.TidmadTaskDataPath()):
        assert declared_rows(scope) == materialized == expected


def test_orchestration_row_declaration_accepts_file_loaded_task_class(
    fixture_data, monkeypatch
):
    """A plugin loaded by filename must not fail an imported-class identity check."""
    import importlib.util
    import sys

    from execute_tools.task_data_path import bind_task_data_path

    from experiments.tidmad.main_orchestrator.validation_rows import declared_rows

    _, _, scope = fixture_data
    name = "synthetic_cold_tidmad_rows"
    spec = importlib.util.spec_from_file_location(name, data_path.__file__)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    foreign_scope = module.TidmadScope(**scope.model_dump())
    assert not isinstance(foreign_scope, data_path.TidmadScope)
    with bind_task_data_path(module.TidmadTaskDataPath()):
        assert declared_rows(foreign_scope) == 8


@pytest.mark.parametrize(
    "limit, expected", [(None, 8), (99, 8), (8, 8), (6, 6), (5, 4), (2, 2)]
)
def test_eval_limit_bounds_materialized_rows_without_changing_training(
    fixture_data, limit, expected
):
    root, profile, _scope = fixture_data
    request = ScopeBuildRequest(
        round_kind="formal",
        selection_strategy="snapshot",
        portion=1.0,
        subset_ref="0,1",
        max_samples=limit,
        task_parameters={"seg_size": ROW_LENGTH},
    )
    adapter = data_path.TidmadTaskDataPath()
    with bind_dataset_profile(profile):
        training = adapter.build_training_scope(request)
        evaluation = adapter.build_eval_scope(request)
    assert sum(map(len, training.sample_set.values())) == 4
    assert len(_materialize(root, evaluation)) == expected
    restored = adapter.deserialize_scope(adapter.serialize_scope(evaluation))
    assert restored.sample_set == evaluation.sample_set
    if limit is None or limit >= 8:
        assert adapter.serialize_scope(evaluation) == adapter.serialize_scope(training)
    else:
        assert evaluation.sample_set == (
            {0: [0]}
            if limit == 2
            else {0: [0, 1]}
            if limit == 5
            else {0: [0, 1], 1: [0]}
        )


def test_limit_below_one_complete_segment_refuses_before_materialization(fixture_data):
    _root, profile, _scope = fixture_data
    request = ScopeBuildRequest(
        round_kind="trial",
        selection_strategy="snapshot",
        portion=1.0,
        max_samples=1,
        task_parameters={"seg_size": ROW_LENGTH},
    )
    with (
        bind_dataset_profile(profile),
        pytest.raises(ValidationScopeError, match="complete PSD"),
    ):
        data_path.TidmadTaskDataPath().build_eval_scope(request)


def test_ceiling_preserves_segment_order_and_numeric_file_order(fixture_data):
    _root, _profile, scope = fixture_data
    selected = scope.model_copy(update={"sample_set": {"1": [1, 0], "0": [1, 0]}})
    bounded = data_path.TidmadTaskDataPath()._bound_evaluation_scope(selected, 6)
    assert list(bounded.sample_set) == ["0", "1"]
    assert bounded.sample_set == {"0": [1, 0], "1": [1]}


def test_capped_scope_cannot_silently_drop_health_monitored_files(fixture_data):
    _root, profile, _scope = fixture_data
    request = ScopeBuildRequest(
        round_kind="formal",
        selection_strategy="snapshot",
        portion=1.0,
        subset_ref="0,1",
        max_samples=4,
        task_parameters={"seg_size": ROW_LENGTH},
    )
    adapter = data_path.TidmadTaskDataPath()
    with bind_dataset_profile(profile):
        evaluation = adapter.build_eval_scope(request)
    coverage = adapter.validate_health_coverage(
        HealthCoverageRequest(
            evaluation_scope=evaluation,
            round_kind="formal",
            health_binding=None,
            health_gate_files=(0, 1),
        )
    )
    assert coverage.applicable and not coverage.covered
    assert evaluation.sample_set == {0: [0, 1]}
    assert "1" in coverage.reason
