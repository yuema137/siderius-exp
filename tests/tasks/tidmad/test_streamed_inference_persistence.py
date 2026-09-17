import json
import math
from pathlib import Path
from typing import ClassVar

import h5py
import numpy as np
import pytest
import torch
from execute_tools.dataset_config import DatasetProfile, tidmad_topology
from execute_tools.evaluation_metric import MetricSpec, PresenceScoreabilityContract
from execute_tools.task_data_path import (
    DeliverableSourceContext,
    DeliverableWriteRequest,
)

from deployments.tidmad_coding_agent_baseline.tools.health import (
    evaluate_candidate_health,
)
from deployments.tidmad_coding_agent_baseline.tools.score import compute_score
from deployments.tidmad_coding_agent_baseline.tools.segment_inference import (
    run_segment_model,
)
from tasks.tidmad.runtime.output_conversion import regression_to_storage
from tasks.tidmad.runtime.scoring import TidmadDenoisingMetric
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


def test_streamed_classification_predictions_are_decoded_and_persisted(
    tmp_path, monkeypatch
):
    """Catch the separated inference host-memory failure from issue #391."""
    profile = DatasetProfile.model_validate_json(
        (PACK_DIR / "resolved" / "dataset_profile.json").read_text(encoding="utf-8")
    )
    topology = tidmad_topology(profile)
    scope = TidmadScope(sample_set={0: [0]}, seg_size=4, profile=profile)
    data_path = TidmadTaskDataPath()
    dataset = _ValidationDataset()
    monkeypatch.setattr(
        data_path, "validation_dataset", lambda _scope, _params: dataset
    )

    def predictions():
        for winning_class in (129, 130):
            logits = torch.zeros(
                (topology.encoding.num_classes, 4), dtype=torch.float32
            )
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
        denoised = handle["timeseries"][topology.channels.input_channel]["timeseries"][
            :
        ]
        injected = handle["timeseries"][topology.channels.target_channel]["timeseries"][
            :
        ]
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
        [
            regression_to_storage(row, value_offset=128, storage_dtype="int8")
            for row in predictions
        ]
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
    # One physical PSD segment is 10 million samples; the model sees 250
    # consecutive 40k windows. This is the smallest real scorer scope.
    psd_length = 10_000_000
    rng = np.random.default_rng(19)
    target = np.clip(
        50 * np.sin(2 * np.pi * 1_200_000 * np.arange(psd_length) / psd_length)
        + rng.normal(0, 4, psd_length),
        -128,
        127,
    ).astype(np.int8)
    raw_values = np.clip(
        target.astype(np.int16) + rng.integers(-8, 9, psd_length), -128, 127
    ).astype(np.int8)
    source = tmp_path / "abra_validation_0000.h5"
    with h5py.File(source, "w") as handle:
        handle.create_dataset("timeseries/channel0001/timeseries", data=raw_values)
        handle.create_dataset("timeseries/channel0002/timeseries", data=target)
        handle["timeseries/channel0001"].attrs["voltage_range_mV"] = 80
        handle["timeseries/channel0001"].attrs["sampling_frequency"] = 10_000_000.0
    cli_dir = tmp_path / "cli"
    cli_dir.mkdir()
    cli_output = cli_dir / "abra_validation_denoised_0000.h5"
    run_segment_model(
        candidate=candidate,
        input_file=source,
        output_file=cli_output,
        device=torch.device("cpu"),
        task_root=PACK_DIR.parents[1],
        required_output_kind="continuous_regression",
    )

    class ValidationDataset:
        file_row_ranges: ClassVar[dict[int, tuple[int, int]]] = {
            0: (0, psd_length // segment_size)
        }
        targets = target.reshape(-1, segment_size)

        def __len__(self):
            return psd_length // segment_size

    profile = DatasetProfile.model_validate_json(
        (PACK_DIR / "resolved" / "dataset_profile.json").read_text()
    )
    scope = TidmadScope(sample_set={0: [0]}, seg_size=segment_size, profile=profile)
    data_path = TidmadTaskDataPath()
    monkeypatch.setattr(
        data_path, "validation_dataset", lambda _scope, _params: ValidationDataset()
    )

    def predictions():
        for row in raw_values.reshape(-1, segment_size):
            offset_input = (
                torch.from_numpy(row.astype(np.int16) + 128).long().unsqueeze(0)
            )
            yield model(offset_input).detach().numpy()[0]

    siderius_dir = tmp_path / "siderius"
    request = DeliverableWriteRequest(
        output_dir=str(siderius_dir),
        exp_id="parity",
        run_name="qualification",
        model_type="regressor",
        task_scope=scope,
        source_context=DeliverableSourceContext(
            data_dir=str(tmp_path), sample_count=psd_length // segment_size
        ),
    )
    data_path.write_deliverable(predictions(), request)
    siderius_output = next(siderius_dir.glob("*.h5"))
    with h5py.File(cli_output) as cli, h5py.File(siderius_output) as siderius:
        path = "timeseries/channel0001/timeseries"
        assert np.array_equal(cli[path][:], siderius[path][:])

    # Replay the same candidate through the CLI scorer and the composed
    # metric's task-owned entry, with one small, identical validation scope.
    scope_path = tmp_path / "scope.json"
    scope_path.write_text('{"0": [0]}')
    cli_score, _ = compute_score(
        input_root=PACK_DIR.parents[1],
        raw_data_dir=tmp_path,
        denoised_dir=cli_dir,
        sample_set_path=scope_path,
        workers=1,
    )
    assert cli_score["scoreable"] and math.isfinite(cli_score["scalar"])
    (tmp_path / "segment_anchors.json").write_bytes(
        (PACK_DIR / "reference_data/segment_anchors.json").read_bytes()
    )
    metric = TidmadDenoisingMetric(
        MetricSpec(
            id="tidmad_denoising_score",
            direction="higher",
            aggregation="tidmad_anchor_normalised_linear_grand_mean",
            references=("anchor_map",),
            scoreability=PresenceScoreabilityContract(),
        )
    )
    fixed_score = metric.evaluate(
        {0: str(siderius_output)},
        evaluation_payload={0: str(siderius_output)},
        task_scope=scope,
        data_dir=str(tmp_path),
    )
    assert fixed_score.scalar == cli_score["scalar"]
    assert fixed_score.per_sample == cli_score["file_vector"]

    cli_health = evaluate_candidate_health(
        input_root=PACK_DIR.parents[1],
        raw_data_dir=tmp_path,
        denoised_paths={0: cli_output},
        file_vector=cli_score["file_vector"],
        scalar=cli_score["scalar"],
        candidate_id="parity",
        run_id="qualification",
        config_root=tmp_path / "cli_health",
    )
    fixed_health = evaluate_candidate_health(
        input_root=PACK_DIR.parents[1],
        raw_data_dir=tmp_path,
        denoised_paths={0: siderius_output},
        file_vector=fixed_score.per_sample,
        scalar=fixed_score.scalar,
        candidate_id="parity",
        run_id="qualification",
        config_root=tmp_path / "fixed_health",
    )
    assert cli_health.status == fixed_health.status
    assert cli_health.eligible == fixed_health.eligible
    assert cli_health.effective_config_sha256 == fixed_health.effective_config_sha256
    assert cli_health.gate_results
    assert [
        (gate["gate_name"], gate["execution_status"], gate["check_passed"])
        for gate in cli_health.gate_results
    ] == [
        (gate["gate_name"], gate["execution_status"], gate["check_passed"])
        for gate in fixed_health.gate_results
    ]
