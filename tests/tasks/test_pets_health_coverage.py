"""Pets' task-owned Health coverage contract."""

from __future__ import annotations

import pytest
from execute_tools.task_data_path import (
    HealthCoverageRequest,
    TaskHealthCoverageError,
)
from nodes.ml_hyperparameter_tune_agent.health_coverage import (
    validate_attempt_health_coverage,
)

from tasks.oxford_iiit_pet.runtime.pets_data_path import (
    PetsItem,
    PetsScope,
    PetsTaskDataPath,
)


def _scope(*image_ids: str) -> PetsScope:
    return PetsScope(
        rows=tuple(PetsItem(image_id=image_id, class_index=0) for image_id in image_ids)
    )


def test_pets_rejects_empty_health_scope() -> None:
    # Build an invalid scope only to exercise this boundary's fail-closed
    # response; normal scope construction rejects empty rows earlier.
    empty_scope = PetsScope.model_construct(rows=())

    result = PetsTaskDataPath().validate_health_coverage(
        HealthCoverageRequest(
            evaluation_scope=empty_scope,
            round_kind="trial",
            health_binding="declared/task_health.yaml",
        )
    )
    assert result.applicable is True
    assert result.covered is False


def test_composed_health_validation_reaches_pets_capability() -> None:
    result = validate_attempt_health_coverage(
        data_path=PetsTaskDataPath(),
        evaluation_scope=_scope("a", "b"),
        round_kind="trial",
        health_binding="declared/task_health.yaml",
        composed=True,
        health_enabled=True,
    )
    assert result is not None and result.covered is True


def test_composed_health_validation_refuses_uncovered_scope() -> None:
    empty_scope = PetsScope.model_construct(rows=())

    with pytest.raises(TaskHealthCoverageError, match="uncovered Health demand"):
        validate_attempt_health_coverage(
            data_path=PetsTaskDataPath(),
            evaluation_scope=empty_scope,
            round_kind="formal",
            health_binding="declared/task_health.yaml",
            composed=True,
            health_enabled=True,
        )
