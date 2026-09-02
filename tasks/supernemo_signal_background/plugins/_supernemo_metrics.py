"""Task-owned energy-matched classification metrics for SuperNEMO."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from execute_tools.evaluation_metric import EvaluationMetric


def _load_data_module():
    module_name = "siderius_exp_supernemo_data"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    path = Path(__file__).with_name("_supernemo_data.py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load SuperNEMO data logic from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_DATA = _load_data_module()
ENERGY_EDGES = _DATA.ENERGY_EDGES
SuperNemoScope = _DATA.SuperNemoScope
materialize_scope = _DATA.materialize_scope
energy_matched_roc = _DATA.energy_matched_roc
weighted_roc = _DATA.weighted_roc


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
