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


class DataDependent(Affine):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if bool(x.sum() > 0):
            return x.float() * self.scale + 1
        return x.float() * self.scale


def test_explicit_trace_rejects_data_dependent_graph_on_comparison_input(tmp_path):
    destination = tmp_path / "candidate"
    with (
        pytest.warns(torch.jit.TracerWarning),
        pytest.raises(ValueError, match="trace qualification"),
    ):
        export_scripted_model(
            DataDependent().eval(),
            examples=[(torch.zeros(1, 7),), (torch.ones(2, 7),)],
            destination=destination,
            method="trace",
        )
    assert not destination.exists()


def test_native_fcnet_regression_exports_by_explicit_trace(tmp_path, monkeypatch):
    # This catches the real conditional-attribute FCNet script failure without
    # changing its native class or substituting a lookalike synthetic model.
    monkeypatch.setenv("SIDERIUS_PLUGIN_DIRS", str(tmp_path))
    from ml_models.models_format_sandbox import get_config_class
    from ml_models.models_sandbox import construct_registered_model

    from deployments.tidmad_coding_agent_baseline.tools.segment_inference import (
        load_candidate_model,
    )

    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        config = get_config_class("fcnet")(segmentation_size=40000, latent_dims=[2])
        model = (
            construct_registered_model("fcnet", config, loss_type="smooth_l1")
            .cpu()
            .eval()
        )
        examples = [
            (torch.zeros(1, 40000, dtype=torch.int64),),
            (torch.arange(80000, dtype=torch.int64).reshape(2, 40000) % 256,),
        ]
        destination = tmp_path / "candidate"
        receipt = export_scripted_model(
            model, examples=examples, destination=destination, method="trace"
        )
        (destination / "architecture.json").write_text(
            '{"version":"tidmad-segment-model-v2","segment_size":40000,'
            '"input_dtype":"int64","output_kind":"continuous_regression"}'
        )
        restored, _ = load_candidate_model(destination, torch.device("cpu"))
        held_out = torch.full((3, 40000), 127, dtype=torch.int64)
        torch.testing.assert_close(restored(held_out), model(held_out))
        assert receipt.serialization_method == "trace"
        assert receipt.example_count == 2
    finally:
        torch.set_num_threads(old_threads)
