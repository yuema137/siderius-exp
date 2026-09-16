"""Task-owned model-I/O parity for the TIDMAD declaration."""

from pathlib import Path

from agent.schemas.model_io_contract import ModelIOContract
from agent.schemas.task_config import ForwardContract
from execute_tools.dataset_config import bind_dataset_profile
from workflows.task_config import load_task_config

TASK_CONFIG = (
    Path(__file__).resolve().parents[3] / "tasks" / "tidmad" / "declared" / "task_config.yaml"
)


def test_normalized_contract_matches_declared_forward_bytes(tidmad_profile) -> None:
    """The task declaration and normalized model contract must stay identical."""
    with bind_dataset_profile(tidmad_profile):
        declared = ForwardContract(**load_task_config(str(TASK_CONFIG))["forward_contract"])
    normalized = ModelIOContract(
        input=declared.model_io.input,
        output=declared.model_io.output,
    )

    assert normalized.input.render() == "[B, T] int64"
    assert normalized.output.render() == "[B, 256, T] float32"
    assert normalized.input.render() == declared.input_shape
    assert normalized.output.render() == declared.output_shape
    assert normalized.class_cardinality == 256
    assert normalized.class_cardinality == declared.num_classes


def test_regression_contract_declares_standard_historical_inference(tidmad_profile) -> None:
    """Fails if real TIDMAD training again emits only an opaque checkpoint."""

    regression = TASK_CONFIG.with_name("task_config_regression.yaml")
    with bind_dataset_profile(tidmad_profile):
        declared = ForwardContract(**load_task_config(str(regression))["forward_contract"])
    inference = declared.model_io.inference

    assert inference is not None
    assert inference.accepted_input_view_formats == ("siderius.numeric-array.v1",)
    assert [item.model_dump(mode="json") for item in inference.required_information] == [
        {"information_class": "data", "fields": []}
    ]
    assert inference.prediction_output_format == "siderius.numeric-array.v1"
    assert (
        inference.prediction_semantic_id == "tidmad.offset-encoded-continuous-waveform-segment.v1"
    )
    assert inference.prediction_decoder_protocol_id == "siderius.identity-prediction-decoder.v1"
