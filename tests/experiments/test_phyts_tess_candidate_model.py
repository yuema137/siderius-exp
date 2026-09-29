"""One loader and one contract: what a candidate must be before it can score.

* ``test_round_trip_predicts_one_scalar_per_curve`` — the happy path, and
  the reachability witness for every refusal below.
* ``test_weights_that_differ_from_the_scripted_model_are_refused`` — the
  tree digest binds bytes, not their agreement; a `weights.pth` that is not
  the parameters inside `model.pt` is exactly what a digest cannot see.
* ``test_a_model_that_returns_a_vector_per_curve_is_refused`` — the task's
  own `write_deliverable` does `reshape(-1)[0]`, which would silently keep
  the first element of a `[B, 2]` output and score it as a prediction.
* ``test_a_curve_without_its_channel_axis_is_refused`` — `[1024]` and
  `[1, 1024]` stack to different batches; the contract says which.
* ``test_a_contract_naming_another_window_is_refused`` — a model traced at
  512 samples loads fine and fails on the first real curve.
* ``test_a_data_bearing_or_linked_candidate_is_refused`` — a candidate
  carries a model; anything else in it is something the caller packed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from experiments.phyts_tess.main_orchestrator.candidate_model import (
    CONTRACT_VERSION,
    load_candidate_model,
    predict_rotation,
    validate_candidate_source,
)
from tasks.phyts_tess.runtime.tess_data_path import SEQUENCE_LENGTH

CPU = torch.device("cpu")
CONTRACT = {
    "version": CONTRACT_VERSION,
    "sequence_length": SEQUENCE_LENGTH,
    "input_dtype": "float32",
    "output_kind": "continuous_scalar",
    "inference_batch_size": 2,
}


class Linear(torch.nn.Module):
    """`[B, 1, L] -> [B, out]`; `out=1` is the contract, `out=2` violates it."""

    def __init__(self, out: int = 1) -> None:
        super().__init__()
        torch.manual_seed(0)
        self.head = torch.nn.Linear(SEQUENCE_LENGTH, out)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.head(value.flatten(1))


def write_candidate(
    root: Path, module: torch.nn.Module, *, contract: dict | None = None
) -> Path:
    root.mkdir(parents=True)
    scripted = torch.jit.trace(module.eval(), torch.zeros(1, 1, SEQUENCE_LENGTH))
    torch.jit.save(scripted, str(root / "model.pt"))
    torch.save(module.state_dict(), root / "weights.pth")
    (root / "contract.json").write_text(json.dumps(contract or CONTRACT))
    (root / "native_reconstruction.json").write_text(
        json.dumps({"model_type": "synthetic_linear"})
    )
    (root / "train_config.json").write_text("{}")
    return root


def _curves(count: int) -> list[torch.Tensor]:
    generator = torch.Generator().manual_seed(1)
    return [torch.randn(1, SEQUENCE_LENGTH, generator=generator) for _ in range(count)]


def test_round_trip_predicts_one_scalar_per_curve(tmp_path):
    module = Linear()
    candidate = write_candidate(tmp_path / "candidate", module)
    validate_candidate_source(candidate)
    model, contract = load_candidate_model(candidate, CPU)
    curves = _curves(5)

    predicted = predict_rotation(
        model, curves, batch_size=contract.inference_batch_size, device=CPU
    )

    with torch.inference_mode():
        expected = [
            float(module(curve.unsqueeze(0)).reshape(-1)[0]) for curve in curves
        ]
    assert predicted == pytest.approx(expected, abs=1e-6)
    assert len(predicted) == 5, "5 curves in 3 batches of 2 must yield exactly 5 values"


def test_weights_that_differ_from_the_scripted_model_are_refused(tmp_path):
    module = Linear()
    candidate = write_candidate(tmp_path / "candidate", module)
    tampered = {name: value + 1.0 for name, value in module.state_dict().items()}
    torch.save(tampered, candidate / "weights.pth")

    with pytest.raises(ValueError, match="differ from model.pt"):
        load_candidate_model(candidate, CPU)


def test_a_model_that_returns_a_vector_per_curve_is_refused(tmp_path):
    candidate = write_candidate(tmp_path / "candidate", Linear(out=2))
    model, contract = load_candidate_model(candidate, CPU)

    with pytest.raises(ValueError, match="one scalar per curve"):
        predict_rotation(
            model, _curves(3), batch_size=contract.inference_batch_size, device=CPU
        )


def test_a_curve_without_its_channel_axis_is_refused(tmp_path):
    candidate = write_candidate(tmp_path / "candidate", Linear())
    model, _ = load_candidate_model(candidate, CPU)

    with pytest.raises(ValueError, match=rf"\[1, {SEQUENCE_LENGTH}\] float32"):
        predict_rotation(
            model, [torch.zeros(SEQUENCE_LENGTH)], batch_size=1, device=CPU
        )


def test_a_contract_naming_another_window_is_refused(tmp_path):
    candidate = write_candidate(
        tmp_path / "candidate", Linear(), contract={**CONTRACT, "sequence_length": 512}
    )

    with pytest.raises(ValueError, match="differs from the task's"):
        load_candidate_model(candidate, CPU)


@pytest.mark.parametrize("defect", ["data", "symlink", "missing"])
def test_a_data_bearing_or_linked_candidate_is_refused(tmp_path, defect):
    candidate = write_candidate(tmp_path / "candidate", Linear())
    if defect == "data":
        (candidate / "val.npz").write_bytes(b"not a model")
    elif defect == "symlink":
        (candidate / "truth").symlink_to(tmp_path)
    else:
        (candidate / "contract.json").rename(candidate / "contract.bak")

    with pytest.raises(ValueError):
        validate_candidate_source(candidate)
