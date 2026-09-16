from pathlib import Path

import h5py
import numpy as np
import pytest
import torch

from execute_tools.dataset_config import DatasetProfile, tidmad_topology
from execute_tools.task_data_path import DeliverableSourceContext, DeliverableWriteRequest
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope, TidmadTaskDataPath
from tasks.tidmad.runtime.output_conversion import regression_to_storage


PACK_DIR = Path(__file__).resolve().parents[3] / "tasks" / "tidmad"


class _ValidationDataset:
    def __init__(self):
        self.file_row_ranges = {0: (0, 2)}
        self.targets = np.array(
            [[-3, -2, -1, 0], [1, 2, 3, 4]],
            dtype=np.int8,
        )

    def __len__(self):
        return 2


def test_streamed_classification_predictions_are_decoded_and_persisted(tmp_path, monkeypatch):
    """Catch the separated inference host-memory failure from issue #391."""
    profile = DatasetProfile.model_validate_json(
        (PACK_DIR / "resolved" / "dataset_profile.json").read_text(encoding="utf-8")
    )
    topology = tidmad_topology(profile)
    scope = TidmadScope(sample_set={0: [0]}, seg_size=4, profile=profile)
    data_path = TidmadTaskDataPath()
    dataset = _ValidationDataset()
    monkeypatch.setattr(data_path, "validation_dataset", lambda _scope, _params: dataset)

    def predictions():
        for winning_class in (129, 130):
            logits = torch.zeros((topology.encoding.num_classes, 4), dtype=torch.float32)
            logits[winning_class] = 1.0
            yield logits

    request = DeliverableWriteRequest(
        output_dir=str(tmp_path),
        exp_id="streamed",
        run_name="qualification",
        model_type="classifier",
        task_scope=scope,
        source_context=DeliverableSourceContext(
            data_dir=str(tmp_path / "unused_data"),
            sample_count=2,
        ),
    )
    data_path.write_deliverable(predictions(), request)

    output = next(tmp_path.glob("*.h5"))
    with h5py.File(output, "r") as handle:
        denoised = handle["timeseries"][topology.channels.input_channel]["timeseries"][:]
        injected = handle["timeseries"][topology.channels.target_channel]["timeseries"][:]
    assert denoised.tolist() == [1, 1, 1, 1, 2, 2, 2, 2]
    assert injected.tolist() == [-3, -2, -1, 0, 1, 2, 3, 4]


def test_streamed_regression_uses_shared_output_conversion(tmp_path, monkeypatch):
    profile = DatasetProfile.model_validate_json(
        (PACK_DIR / "resolved" / "dataset_profile.json").read_text()
    )
    scope = TidmadScope(sample_set={0: [0]}, seg_size=4, profile=profile)
    data_path = TidmadTaskDataPath()
    monkeypatch.setattr(
        data_path, "validation_dataset", lambda _scope, _params: _ValidationDataset()
    )
    predictions = [
        np.array([128.9, 129.9, 130.9, 131.9], dtype=np.float32),
        np.array([132.9, 133.9, 134.9, 135.9], dtype=np.float32),
    ]
    request = DeliverableWriteRequest(
        output_dir=str(tmp_path),
        exp_id="regression",
        run_name="qualification",
        model_type="regressor",
        task_scope=scope,
        source_context=DeliverableSourceContext(data_dir=str(tmp_path), sample_count=2),
    )
    data_path.write_deliverable(iter(predictions), request)
    output = next(tmp_path.glob("*.h5"))
    with h5py.File(output) as handle:
        actual = handle["timeseries/channel0001/timeseries"][:]
    expected = np.concatenate(
        [regression_to_storage(row, value_offset=128, storage_dtype="int8") for row in predictions]
    )
    assert np.array_equal(actual, expected)


def test_streamed_regression_refuses_nonfinite_predictions(tmp_path, monkeypatch):
    profile = DatasetProfile.model_validate_json(
        (PACK_DIR / "resolved" / "dataset_profile.json").read_text()
    )
    scope = TidmadScope(sample_set={0: [0]}, seg_size=4, profile=profile)
    data_path = TidmadTaskDataPath()
    monkeypatch.setattr(
        data_path, "validation_dataset", lambda _scope, _params: _ValidationDataset()
    )
    request = DeliverableWriteRequest(
        output_dir=str(tmp_path),
        exp_id="regression",
        run_name="qualification",
        model_type="regressor",
        task_scope=scope,
        source_context=DeliverableSourceContext(data_dir=str(tmp_path), sample_count=2),
    )
    with pytest.raises(ValueError, match="non-finite"):
        data_path.write_deliverable(
            iter([np.array([128.0, np.nan, 128.0, 128.0], dtype=np.float32)]),
            request,
        )
    assert not list(tmp_path.glob("*.h5"))
