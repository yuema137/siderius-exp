"""Official metric arithmetic for the NatureBench cancer-gene task."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

import h5py
import numpy as np

from execute_tools.evaluation_metric import EvaluationMetric


def _average_precision(labels: np.ndarray, predictions: np.ndarray) -> float:
    """Binary average precision with threshold ties grouped like sklearn."""
    truth = np.asarray(labels, dtype=np.int64)
    scores = np.asarray(predictions, dtype=np.float64)
    positives = int(truth.sum())
    if positives == 0:
        raise ValueError("AUPRC is undefined when an evaluation split has no positives")
    order = np.argsort(scores, kind="mergesort")[::-1]
    truth = truth[order]
    scores = scores[order]
    distinct = np.r_[np.where(np.diff(scores))[0], len(scores) - 1]
    true_positives = np.cumsum(truth)[distinct]
    false_positives = 1 + distinct - true_positives
    recall = true_positives / positives
    precision = true_positives / (true_positives + false_positives)
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


def _roc_auc(labels: np.ndarray, predictions: np.ndarray) -> float:
    """Binary ROC AUC from average ranks, including exact score ties."""
    truth = np.asarray(labels, dtype=np.int64)
    scores = np.asarray(predictions, dtype=np.float64)
    positives = int(truth.sum())
    negatives = len(truth) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("AUROC needs both positive and negative evaluation labels")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=np.float64)
    start = 0
    while start < len(scores):
        stop = start + 1
        while stop < len(scores) and scores[order[stop]] == scores[order[start]]:
            stop += 1
        ranks[order[start:stop]] = (start + 1 + stop) / 2.0
        start = stop
    rank_sum = float(ranks[truth == 1].sum())
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def _scores(
    evaluation_payload: Mapping[str, np.ndarray], task_scope: Any, data_dir: str
) -> tuple[list[float], list[float]]:
    instances = getattr(task_scope, "instances", None)
    split = getattr(task_scope, "evaluation_split", None)
    if not instances or split not in {"val", "test"}:
        raise ValueError("cancer-gene metrics require a non-empty CancerGeneScope")
    if split == "test":
        raise ValueError(
            "test labels are intentionally absent from the task package; use the untouched "
            "NatureBench evaluator for official test scoring"
        )
    auprc: list[float] = []
    auroc: list[float] = []
    for name in instances:
        if name not in evaluation_payload:
            raise ValueError(f"cancer-gene deliverable is missing network {name!r}")
        with h5py.File(f"{data_dir}/{name}/data.h5", "r") as handle:
            mask = np.asarray(handle["mask_val"]).astype(bool).reshape(-1)
            labels = np.asarray(handle["y_val"]).reshape(-1)[mask]
        predictions = np.asarray(evaluation_payload[name], dtype=np.float64).reshape(-1)
        if len(predictions) != int(mask.sum()):
            raise ValueError(
                f"network {name!r} needs {int(mask.sum())} validation predictions; "
                f"got {len(predictions)}"
            )
        auprc.append(_average_precision(labels, predictions))
        auroc.append(_roc_auc(labels, predictions))
    return auprc, auroc


class CancerGeneMeanAuprcMetric(EvaluationMetric):
    """Unweighted mean of per-network AUPRC, matching the benchmark headline."""

    IMPLEMENTS: ClassVar[tuple[str, ...]] = ("mean_auprc",)

    def _compute(
        self,
        deliverables: Mapping[int, str],
        /,
        *,
        evaluation_payload: Mapping[str, np.ndarray],
        task_scope: Any,
        data_dir: str,
    ) -> tuple[float, list[float | None] | None, tuple[str, ...]]:
        auprc, _ = _scores(evaluation_payload, task_scope, data_dir)
        return float(np.mean(auprc)), list(auprc), tuple(task_scope.instances)


class CancerGeneMeanAurocMetric(EvaluationMetric):
    """Observational unweighted mean AUROC over the same network set."""

    IMPLEMENTS: ClassVar[tuple[str, ...]] = ("mean_auroc",)

    def _compute(
        self,
        deliverables: Mapping[int, str],
        /,
        *,
        evaluation_payload: Mapping[str, np.ndarray],
        task_scope: Any,
        data_dir: str,
    ) -> tuple[float, list[float | None] | None, tuple[str, ...]]:
        _, auroc = _scores(evaluation_payload, task_scope, data_dir)
        return float(np.mean(auroc)), list(auroc), tuple(task_scope.instances)
