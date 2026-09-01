"""TIDMAD proposal validation against the task-owned segmentation contract."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent.schemas.hyperparam_tuning import ExpertAdvice
from agent.schemas.proposal import ProposalOutput
from execute_tools.dataset_config import DatasetProfile, bind_dataset_profile

TASK_ROOT = Path(__file__).resolve().parents[3] / "tasks" / "tidmad"
PSD_SEGMENT_LENGTH = 10_000_000


@pytest.fixture(scope="module")
def task_profile() -> DatasetProfile:
    raw = json.loads((TASK_ROOT / "resolved" / "dataset_profile.json").read_text())
    return DatasetProfile.model_validate(raw)


@pytest.fixture
def expert_advice() -> ExpertAdvice:
    return ExpertAdvice(
        focus_areas=["start with depth=2"],
        constraints=["VRAM < 8 GB"],
        known_failures=["large batch_size"],
        suggested_directions=["try focal gamma=2"],
        rationale="fixture",
    )


def _make_output(
    expert_advice: ExpertAdvice, model_config: dict | None
) -> ProposalOutput:
    baseline_config = {
        "train_config": {"lr": 1e-4, "epochs": 1},
        "loss_config": {"loss_type": "focal"},
    }
    if model_config is not None:
        baseline_config["model_config"] = model_config
    return ProposalOutput(
        model_name="candidate",
        model_description="fixture",
        mathematical_definition="fixture",
        motivation="fixture",
        expert_advice=expert_advice,
        baseline_config=baseline_config,
    )


@pytest.mark.parametrize("segmentation_size", [100, 1_000, 1_250, 16_000, 50_000])
def test_declared_divisors_are_accepted(
    expert_advice: ExpertAdvice,
    task_profile: DatasetProfile,
    segmentation_size: int,
) -> None:
    assert PSD_SEGMENT_LENGTH % segmentation_size == 0
    with bind_dataset_profile(task_profile):
        output = _make_output(expert_advice, {"segmentation_size": segmentation_size})
    assert (
        output.baseline_config["model_config"]["segmentation_size"] == segmentation_size
    )


def test_nondivisor_is_refused_with_actionable_values(
    expert_advice: ExpertAdvice, task_profile: DatasetProfile
) -> None:
    with bind_dataset_profile(task_profile), pytest.raises(ValidationError) as exc:
        _make_output(expert_advice, {"segmentation_size": 16_384})
    message = str(exc.value)
    assert "segmentation_size" in message
    assert "16384" in message
    assert "10000000" in message
    assert "Valid segmentation_size values" in message
    assert "16000" in message


@pytest.mark.parametrize("invalid", [-100, 0, "16000"])
def test_invalid_values_are_refused(
    expert_advice: ExpertAdvice,
    task_profile: DatasetProfile,
    invalid: object,
) -> None:
    with (
        bind_dataset_profile(task_profile),
        pytest.raises(ValidationError, match="segmentation_size"),
    ):
        _make_output(expert_advice, {"segmentation_size": invalid})


@pytest.mark.parametrize("model_config", [{"depth": 4}, None])
def test_absent_segmentation_constraint_is_a_no_op(
    expert_advice: ExpertAdvice,
    task_profile: DatasetProfile,
    model_config: dict | None,
) -> None:
    with bind_dataset_profile(task_profile):
        output = _make_output(expert_advice, model_config)
    if model_config is None:
        assert "model_config" not in output.baseline_config
    else:
        assert "segmentation_size" not in output.baseline_config["model_config"]


def test_empty_baseline_config_remains_compatible(
    expert_advice: ExpertAdvice, task_profile: DatasetProfile
) -> None:
    with bind_dataset_profile(task_profile):
        output = ProposalOutput(
            model_name="candidate",
            model_description="fixture",
            mathematical_definition="fixture",
            motivation="fixture",
            expert_advice=expert_advice,
            baseline_config={},
        )
    assert output.baseline_config == {}
