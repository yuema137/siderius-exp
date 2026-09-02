"""Task-owned energy-matched classification metrics for Majorana."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
from execute_tools.evaluation_metric import EvaluationMetric


def _load_data_module():
    name = "siderius_exp_majorana_data"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name("_majorana_data.py")
    )
    if spec is None or spec.loader is None:
        raise ImportError("cannot load Majorana data logic")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_DATA = _load_data_module()
ENERGY_EDGES = _DATA.ENERGY_EDGES
MajoranaScope = _DATA.MajoranaScope
materialize_scope = _DATA.materialize_scope


def _values(payload: np.ndarray, task_scope: Any, data_dir: str):
    if not isinstance(task_scope, MajoranaScope):
        raise TypeError("Majorana metric requires its declared evaluation scope")
    events = materialize_scope(task_scope, data_dir)
    scores = np.asarray(payload, dtype=np.float64).reshape(-1)
    if scores.size != events.labels.size:
        raise ValueError(
            f"Majorana scope needs {events.labels.size} predictions; got {scores.size}"
        )
    if not np.all(np.isfinite(scores)) or np.any((scores < 0) | (scores > 1)):
        raise ValueError("Majorana predictions must be finite probabilities in [0, 1]")
    return events.labels, scores, events.energies


def _weighted_auc(labels: np.ndarray, scores: np.ndarray, weights: np.ndarray) -> float:
    active = weights > 0
    labels, scores, weights = labels[active], scores[active], weights[active]
    positive = float(weights[labels == 1].sum())
    negative = float(weights[labels == 0].sum())
    if positive <= 0 or negative <= 0:
        raise ValueError("ROC AUC requires both classes")
    order = np.argsort(-scores, kind="mergesort")
    labels, scores, weights = labels[order], scores[order], weights[order]
    tp = np.cumsum(weights * (labels == 1))
    fp = np.cumsum(weights * (labels == 0))
    ends = np.flatnonzero(np.r_[scores[1:] != scores[:-1], True])
    return float(
        np.trapezoid(np.r_[0.0, tp[ends] / positive], np.r_[0.0, fp[ends] / negative])
    )


def _energy_weights(labels: np.ndarray, energies: np.ndarray) -> np.ndarray:
    bins = np.searchsorted(ENERGY_EDGES, energies, side="right") - 1
    weights = np.zeros(labels.size, dtype=np.float64)
    for bin_id in np.unique(bins):
        if bin_id < 0 or bin_id >= ENERGY_EDGES.size - 1:
            continue
        in_bin = bins == bin_id
        negative, positive = in_bin & (labels == 0), in_bin & (labels == 1)
        common = min(int(negative.sum()), int(positive.sum()))
        if common:
            weights[negative] = common / int(negative.sum())
            weights[positive] = common / int(positive.sum())
    return weights


class MajoranaEnergyMatchedAuc(EvaluationMetric):
    IMPLEMENTS: ClassVar[tuple[str, ...]] = ("energy_matched_roc_auc",)

    def _compute(self, deliverables, /, *, evaluation_payload, task_scope, data_dir):
        labels, scores, energies = _values(evaluation_payload, task_scope, data_dir)
        return (
            _weighted_auc(labels, scores, _energy_weights(labels, energies)),
            None,
            (),
        )


class MajoranaOrdinaryAuc(EvaluationMetric):
    IMPLEMENTS: ClassVar[tuple[str, ...]] = ("ordinary_roc_auc",)

    def _compute(self, deliverables, /, *, evaluation_payload, task_scope, data_dir):
        labels, scores, _ = _values(evaluation_payload, task_scope, data_dir)
        return _weighted_auc(labels, scores, np.ones(labels.size)), None, ()
