"""Frozen TIDMAD V18 runtime-estimation incident oracle."""

import json
from pathlib import Path

from agent.skills.training_skill.estimator import (
    _total_train_steps,
    estimate_wall_time_seconds,
)
from execute_tools.dataset_config import DatasetProfile

TASK_ROOT = Path(__file__).resolve().parents[3] / "tasks" / "tidmad"
INCIDENT_SAMPLE_SET = {str(index): list(range(20)) for index in range(4, 10)}


def _profile() -> DatasetProfile:
    raw = json.loads((TASK_ROOT / "resolved" / "dataset_profile.json").read_text())
    return DatasetProfile.model_validate(raw)


def _incident_kwargs() -> dict:
    return {
        "model_type": "incident_candidate",
        "model_config": {"segmentation_size": 1_250},
        "train_config": {"batch_size": 2, "epochs": 1},
        "sample_set": INCIDENT_SAMPLE_SET,
        "train_portion": 1.0,
        "num_params": 141_280,
        "dataset_profile": _profile(),
    }


def test_incident_scope_resolves_exactly_480000_steps() -> None:
    steps = _total_train_steps(
        INCIDENT_SAMPLE_SET,
        seg_size=1_250,
        batch_size=2,
        train_portion=1.0,
        epochs=1,
        profile=_profile(),
    )
    assert steps == 480_000


def test_static_prior_underprices_the_incident_and_cannot_admit_formal() -> None:
    result = estimate_wall_time_seconds(**_incident_kwargs(), ms_per_step=None)
    assert result["seconds"] / 60 < 120
    assert result["breakdown"]["ms_source"] == "static_uncalibrated"
    assert result["breakdown"]["formal_execution_eligible"] is False


def test_measured_incident_cost_exceeds_the_formal_budget() -> None:
    result = estimate_wall_time_seconds(**_incident_kwargs(), ms_per_step=44.3)
    assert result["seconds"] / 60 > 120
    assert result["breakdown"]["ms_source"] == "real_dataset_warmup"
    assert result["breakdown"]["formal_execution_eligible"] is True
