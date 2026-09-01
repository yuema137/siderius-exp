"""Task-owned model-I/O parity for the TIDMAD declaration."""

from pathlib import Path

from agent.schemas.model_io_contract import ModelIOContract
from agent.schemas.task_config import ForwardContract
from workflows.task_config import load_task_config

TASK_CONFIG = Path(__file__).resolve().parents[3] / "tasks" / "tidmad" / "declared" / "task_config.yaml"


def test_normalized_contract_matches_declared_forward_bytes() -> None:
    """The task declaration and normalized model contract must stay identical."""
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
