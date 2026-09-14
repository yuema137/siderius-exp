"""Task-owned Health coverage declarations for Health-enabled task packs."""

from __future__ import annotations

from pathlib import Path

import pytest
from execute_tools.dataset_config import DatasetProfile
from execute_tools.task_data_path import HealthCoverageRequest, TaskHealthCoverageError
from nodes.ml_hyperparameter_tune_agent.health_coverage import (
    validate_attempt_health_coverage,
)

from tasks.davis_future_prediction.runtime.davis_data_path import (
    DavisClip,
    DavisScope,
    DavisTaskDataPath,
)
from tasks.oxford_iiit_pet.runtime.pets_data_path import (
    PetsItem,
    PetsScope,
    PetsTaskDataPath,
)
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope, TidmadTaskDataPath


def _request(scope: object, *, files: tuple[int, ...] | None = None):
    return HealthCoverageRequest(
        evaluation_scope=scope,
        round_kind="formal",
        health_binding="declared/task_health.yaml",
        health_gate_files=files,
    )


def test_pets_requires_nonempty_exact_evaluation_scope() -> None:
    task = PetsTaskDataPath()
    result = task.validate_health_coverage(
        _request(PetsScope(rows=(PetsItem(image_id="a", class_index=0),)))
    )
    assert result.covered is True


def test_davis_requires_nonempty_exact_evaluation_scope() -> None:
    task = DavisTaskDataPath()
    result = task.validate_health_coverage(
        _request(DavisScope(rows=(DavisClip(sequence_name="bear", start_frame=0),)))
    )
    assert result.covered is True


def test_tidmad_requires_every_resolved_monitored_file() -> None:
    task = TidmadTaskDataPath()
    scope = TidmadScope(sample_set={3: [0], 10: [0], 17: [0]}, seg_size=1)
    result = task.validate_health_coverage(_request(scope, files=(3, 10, 17)))
    assert result.covered is True


def test_tidmad_refuses_missing_monitored_file() -> None:
    task = TidmadTaskDataPath()
    scope = TidmadScope(sample_set={3: [0], 10: [0]}, seg_size=1)
    with pytest.raises(TaskHealthCoverageError, match="uncovered Health demand"):
        validate_attempt_health_coverage(
            data_path=task,
            evaluation_scope=scope,
            round_kind="formal",
            health_binding="declared/task_health.yaml",
            health_gate_files=(3, 10, 17),
            composed=True,
            health_enabled=True,
        )


def test_tidmad_refuses_when_resolved_monitored_files_are_absent() -> None:
    task = TidmadTaskDataPath()
    scope = TidmadScope(sample_set={3: [0], 10: [0], 17: [0]}, seg_size=1)
    result = task.validate_health_coverage(
        _request(scope, files=(3, 10))
    )
    assert result.covered is True
    with pytest.raises(TaskHealthCoverageError, match="effective monitored"):
        validate_attempt_health_coverage(
            data_path=task,
            evaluation_scope=scope,
            round_kind="trial",
            health_binding="declared/task_health.yaml",
            composed=True,
            health_enabled=True,
        )


def test_tidmad_none_binding_uses_full_health_demand() -> None:
    task = TidmadTaskDataPath()
    profile = DatasetProfile.model_construct(
        partition_count=20,
        topology={},
        anchor_selection_files=[0],
        health_peek_files=[3, 10, 17],
    )
    scope = TidmadScope(
        sample_set={index: [0] for index in range(20)}, seg_size=1, profile=profile
    )
    binding = str(Path(__file__).parents[2] / "tasks/tidmad/framework_configs/health.yaml")
    result = task.validate_health_coverage(
        _request(scope, files=None).model_copy(update={"health_binding": binding})
    )
    assert result.covered is True


def test_tidmad_none_binding_refuses_partial_full_health_demand() -> None:
    task = TidmadTaskDataPath()
    profile = DatasetProfile.model_construct(
        partition_count=20,
        topology={},
        anchor_selection_files=[0],
        health_peek_files=[3, 10, 17],
    )
    scope = TidmadScope(sample_set={0: [0], 1: [0]}, seg_size=1, profile=profile)
    binding = str(Path(__file__).parents[2] / "tasks/tidmad/framework_configs/health.yaml")
    with pytest.raises(TaskHealthCoverageError, match="uncovered Health demand"):
        validate_attempt_health_coverage(
            data_path=task,
            evaluation_scope=scope,
            round_kind="formal",
            health_binding=binding,
            composed=True,
            health_enabled=True,
        )
