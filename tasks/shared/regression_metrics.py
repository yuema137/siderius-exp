"""Global physical-unit regression scores for task-owned scope/target codecs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

import numpy as np
from execute_tools.evaluation_metric import EvaluationMetric


def paired(
    payload: Mapping[str, float], scope: Any, data_dir: str | None
) -> tuple[np.ndarray, np.ndarray]:
    if data_dir is None:
        raise ValueError("trusted scoring requires the prepared data directory")
    if set(payload) != set(scope.keys):
        raise ValueError("predictions must cover exactly the evaluation scope")
    truth = scope.truth(data_dir)
    prediction = np.asarray([payload[key] for key in scope.keys], dtype=np.float64)
    if not np.isfinite(truth).all() or not np.isfinite(prediction).all():
        raise ValueError("non-finite target or prediction")
    return truth, prediction


class RegressionRmse(EvaluationMetric):
    IMPLEMENTS: ClassVar[tuple[str, ...]] = ("rmse",)

    def _compute(
        self,
        deliverables: Mapping[int, str],
        /,
        *,
        evaluation_payload: Any,
        task_scope: Any,
        data_dir: str | None = None,
    ):
        truth, prediction = paired(evaluation_payload, task_scope, data_dir)
        return float(np.sqrt(np.mean(np.square(truth - prediction)))), None, ()


class RegressionR2(EvaluationMetric):
    IMPLEMENTS: ClassVar[tuple[str, ...]] = ("r2",)

    def _compute(
        self,
        deliverables: Mapping[int, str],
        /,
        *,
        evaluation_payload: Any,
        task_scope: Any,
        data_dir: str | None = None,
    ):
        truth, prediction = paired(evaluation_payload, task_scope, data_dir)
        total = np.square(truth - truth.mean()).sum()
        if total <= 0:
            raise ValueError("R2 is undefined for zero target variance")
        return float(1 - np.square(truth - prediction).sum() / total), None, ()
