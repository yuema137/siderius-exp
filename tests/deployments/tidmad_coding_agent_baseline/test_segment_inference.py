from __future__ import annotations

import json

import h5py
import numpy as np
import pytest
import torch
from deployments.tidmad_coding_agent_baseline.tools.segment_inference import (
    SEGMENT_SIZE,
    load_candidate_model,
    run_segment_model,
)


class _IdentityClassifier(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.embedding = torch.nn.Embedding(256, 256)
        with torch.no_grad():
            self.embedding.weight.zero_()
            self.embedding.weight.diagonal().fill_(1.0)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.embedding(values).transpose(1, 2)


def _candidate(root):
    root.mkdir()
    model = _IdentityClassifier().eval()
    traced = torch.jit.trace(model, torch.zeros((1, SEGMENT_SIZE), dtype=torch.int64))
    traced.save(str(root / "model.pt"))
    torch.save(model.state_dict(), root / "weights.pth")
    (root / "model.py").write_text("# source retained for reproduction\n")
    (root / "train_config.json").write_text('{"epochs":1}\n')
    (root / "architecture.json").write_text(
        json.dumps(
            {
                "version": "tidmad-segment-model-v1",
                "segment_size": SEGMENT_SIZE,
                "input_dtype": "int64",
                "output_kind": "categorical_logits",
                "num_classes": 256,
                "inference_batch_size": 1,
            }
        )
    )
    return root


def test_evaluator_owns_segmentation_decoding_and_hdf5_write(tmp_path):
    candidate = _candidate(tmp_path / "candidate")
    source = tmp_path / "input.h5"
    expected = np.arange(SEGMENT_SIZE, dtype=np.int64).astype(np.int8)
    with h5py.File(source, "w") as handle:
        channel = handle.require_group("timeseries").create_group("channel0001")
        channel.attrs["sampling_frequency"] = 10_000_000
        channel.attrs["voltage_range_mV"] = 80
        channel.create_dataset("timeseries", data=expected)

    output = tmp_path / "output.h5"
    run_segment_model(
        candidate=candidate,
        input_file=source,
        output_file=output,
        device=torch.device("cpu"),
    )

    assert output.with_suffix(".h5.complete").read_text() == "complete\n"
    with h5py.File(output, "r") as handle:
        observed = handle["timeseries/channel0001/timeseries"][:]
        assert np.array_equal(observed, expected)
        assert handle["timeseries/channel0001"].attrs["voltage_range_mV"] == 80


def test_model_artifact_must_have_matching_nonempty_weights(tmp_path):
    candidate = _candidate(tmp_path / "candidate")
    torch.save({"wrong": torch.ones(1)}, candidate / "weights.pth")

    with pytest.raises(ValueError, match="keys do not match"):
        load_candidate_model(candidate, torch.device("cpu"))
