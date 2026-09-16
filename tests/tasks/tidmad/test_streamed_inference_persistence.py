import json
from pathlib import Path

import h5py
import numpy as np
import pytest
import torch
from execute_tools.dataset_config import DatasetProfile, tidmad_topology
from execute_tools.task_data_path import (
    DeliverableSourceContext,
    DeliverableWriteRequest,
)

from deployments.tidmad_coding_agent_baseline.tools.segment_inference import (
    run_segment_model,
)
from tasks.tidmad.runtime.output_conversion import regression_to_storage
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope, TidmadTaskDataPath

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


def test_same_regression_candidate_has_identical_cli_and_siderius_deliverables(
    tmp_path, monkeypatch
):
    """A shared codec must yield identical persisted samples for both callers."""

    class Regressor(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.scale = torch.nn.Parameter(torch.tensor(1.0))

        def forward(self, values):
            return values.float() * self.scale + 0.9

    candidate = tmp_path / "candidate"
    candidate.mkdir()
    model = Regressor().eval()
    segment_size = 40_000
    torch.jit.trace(model, torch.zeros((1, segment_size), dtype=torch.int64)).save(
        str(candidate / "model.pt")
    )
    torch.save(model.state_dict(), candidate / "weights.pth")
    (candidate / "architecture.json").write_text(
        json.dumps(
            {
                "version": "tidmad-segment-model-v2",
                "segment_size": segment_size,
                "input_dtype": "int64",
                "output_kind": "continuous_regression",
                "inference_batch_size": 1,
            }
        )
    )
    raw_values = (np.arange(segment_size) % 256 - 128).astype(np.int8)
    source = tmp_path / "raw.h5"
    with h5py.File(source, "w") as handle:
        handle.create_dataset("timeseries/channel0001/timeseries", data=raw_values)
    cli_output = tmp_path / "cli.h5"
    run_segment_model(
        candidate=candidate,
        input_file=source,
        output_file=cli_output,
        device=torch.device("cpu"),
        task_root=PACK_DIR.parents[1],
        required_output_kind="continuous_regression",
    )

    class ValidationDataset:
        file_row_ranges = {0: (0, 1)}
        targets = np.zeros((1, segment_size), dtype=np.int8)

        def __len__(self):
            return 1

    profile = DatasetProfile.model_validate_json(
        (PACK_DIR / "resolved" / "dataset_profile.json").read_text()
    )
    scope = TidmadScope(sample_set={0: [0]}, seg_size=segment_size, profile=profile)
    data_path = TidmadTaskDataPath()
    monkeypatch.setattr(
        data_path, "validation_dataset", lambda _scope, _params: ValidationDataset()
    )
    offset_input = (
        torch.from_numpy(raw_values.astype(np.int16) + 128).long().unsqueeze(0)
    )
    prediction = model(offset_input).detach().numpy()[0]
    siderius_dir = tmp_path / "siderius"
    request = DeliverableWriteRequest(
        output_dir=str(siderius_dir),
        exp_id="parity",
        run_name="qualification",
        model_type="regressor",
        task_scope=scope,
        source_context=DeliverableSourceContext(data_dir=str(tmp_path), sample_count=1),
    )
    data_path.write_deliverable(iter([prediction]), request)
    siderius_output = next(siderius_dir.glob("*.h5"))
    with h5py.File(cli_output) as cli, h5py.File(siderius_output) as siderius:
        path = "timeseries/channel0001/timeseries"
        assert np.array_equal(cli[path][:], siderius[path][:])
