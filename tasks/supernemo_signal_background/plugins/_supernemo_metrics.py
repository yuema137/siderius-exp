"""Task-owned energy-matched classification metrics for SuperNEMO."""

from __future__ import annotations

from typing import Any, ClassVar

import numpy as np
from execute_tools.evaluation_metric import EvaluationMetric

from ._supernemo_data import (
    ENERGY_EDGES,
    SuperNemoScope,
    energy_matched_roc,
    materialize_scope,
    weighted_roc,
)


def _values(
    payload: np.ndarray, task_scope: Any, data_dir: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not isinstance(task_scope, SuperNemoScope):
        raise TypeError("SuperNEMO metric requires its declared evaluation scope")
    events = materialize_scope(task_scope, data_dir)
    scores = np.asarray(payload, dtype=np.float64)
    if scores.size != events.labels.size:
        raise ValueError(
            f"SuperNEMO scope needs {events.labels.size} predictions; got {scores.size}"
        )
    if not np.all(np.isfinite(scores)) or np.any((scores < 0) | (scores > 1)):
        raise ValueError("SuperNEMO predictions must be finite probabilities in [0, 1]")
    return events.labels, scores, events.energy_sum


class SuperNemoEnergyMatchedAuc(EvaluationMetric):
    IMPLEMENTS: ClassVar[tuple[str, ...]] = ("energy_matched_roc_auc",)

    def _compute(
        self,
        deliverables,
        /,
        *,
        evaluation_payload: np.ndarray,
        task_scope: Any,
        data_dir: str,
    ) -> tuple[float, None, tuple[str, ...]]:
        labels, scores, energy = _values(evaluation_payload, task_scope, data_dir)
        result = energy_matched_roc(labels, scores, energy, ENERGY_EDGES)
        return result.auc, None, ()


class SuperNemoOrdinaryAuc(EvaluationMetric):
    IMPLEMENTS: ClassVar[tuple[str, ...]] = ("ordinary_roc_auc",)

    def _compute(
        self,
        deliverables,
        /,
        *,
        evaluation_payload: np.ndarray,
        task_scope: Any,
        data_dir: str,
    ) -> tuple[float, None, tuple[str, ...]]:
        labels, scores, _ = _values(evaluation_payload, task_scope, data_dir)
        *_, auc = weighted_roc(labels, scores, np.ones(labels.size))
        return auc, None, ()
