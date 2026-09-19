"""Serialization must preserve behavior/state and remain evaluator-loadable."""

import pytest
import torch

from experiments.shared.scripted_model_export import export_scripted_model


class Affine(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.scale = torch.nn.Parameter(torch.tensor(1.5))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x.float() * self.scale


class Stateful(Affine):
    def __init__(self):
        super().__init__()
        self.register_buffer("counter", torch.tensor(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        self.counter.add_(1)
        return x.float() * self.scale


class DifferentScript(Affine):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if torch.jit.is_scripting():
            return x.float() * self.scale + 1
        return x.float() * self.scale


class Unscriptable(Affine):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        operation = lambda y: y.float() * self.scale
        return operation(x)


@pytest.mark.parametrize(
    "model,reason",
    [
        (Stateful, "changed parameter or buffer"),
        (DifferentScript, "output differs"),
        (Unscriptable, "no trace fallback"),
    ],
)
def test_invalid_export_never_publishes_candidate(tmp_path, model, reason):
    destination = tmp_path / "candidate"
    with pytest.raises(ValueError, match=reason):
        export_scripted_model(
            model().eval(), examples=[(torch.arange(7),)], destination=destination
        )
    assert not destination.exists()


def test_export_loads_in_existing_evaluator_and_preserves_existing_destination(
    tmp_path,
):
    from deployments.tidmad_coding_agent_baseline.tools.segment_inference import (
        SegmentModelContract,
        load_candidate_model,
    )

    contract = SegmentModelContract(
        version="tidmad-segment-model-v2",
        segment_size=40000,
        input_dtype="int64",
        output_kind="continuous_regression",
    )
    destination = tmp_path / "candidate"
    model = Affine().eval()
    examples = [
        (torch.zeros(1, 40000, dtype=torch.int64),),
        (torch.ones(2, 40000, dtype=torch.int64),),
    ]
    export_scripted_model(model, examples=examples, destination=destination)
    (destination / "architecture.json").write_text(contract.model_dump_json())
    restored, _ = load_candidate_model(destination, torch.device("cpu"))
    assert torch.equal(restored(examples[1][0]), torch.full((2, 40000), 1.5))
    original = (destination / "model.pt").read_bytes()
    with pytest.raises(FileExistsError):
        export_scripted_model(
            Affine().eval(), examples=examples, destination=destination
        )
    assert (destination / "model.pt").read_bytes() == original


def test_failed_serialization_removes_only_new_destination(tmp_path, monkeypatch):
    def fail(*_):
        raise OSError("disk write failed")

    monkeypatch.setattr(torch.jit, "save", fail)
    destination = tmp_path / "candidate"
    with pytest.raises(OSError, match="disk write failed"):
        export_scripted_model(
            Affine().eval(), examples=[(torch.ones(3),)], destination=destination
        )
    assert not destination.exists()
