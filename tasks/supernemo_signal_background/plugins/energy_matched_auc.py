"""Deterministic energy-matched ROC AUC for the SuperNEMO task."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class EnergyMatchedRoc:
    """One energy-matched ROC result and its scoreability evidence."""

    auc: float
    false_positive_rate: np.ndarray
    true_positive_rate: np.ndarray
    thresholds: np.ndarray
    event_weights: np.ndarray
    included_events: int
    excluded_events: int
    included_signal: int
    included_background: int
    common_bins: int
    total_bins: int


@dataclass(frozen=True, slots=True)
class EnergyBalancedSelection:
    """Deterministic event indices balanced by class inside every energy bin."""

    indices: np.ndarray
    common_bins: int
    selected_signal: int
    selected_background: int
    excluded_events: int


def _validated_vectors(
    labels: np.ndarray, scores: np.ndarray, energy_sum: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    checked_labels = np.asarray(labels).reshape(-1)
    checked_scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    checked_energy = np.asarray(energy_sum, dtype=np.float64).reshape(-1)
    if not (checked_labels.size == checked_scores.size == checked_energy.size):
        raise ValueError("labels, scores, and energy_sum must have equal lengths")
    if checked_labels.size == 0:
        raise ValueError("energy-matched ROC requires at least one event")
    if not np.all(np.isin(checked_labels, (0, 1))):
        raise ValueError("labels must be binary values 0 or 1")
    if not np.all(np.isfinite(checked_scores)):
        raise ValueError("scores must be finite")
    if not np.all(np.isfinite(checked_energy)):
        raise ValueError("energy_sum must be finite")
    return checked_labels.astype(np.uint8), checked_scores, checked_energy


def energy_matching_weights(
    labels: np.ndarray,
    energy_sum: np.ndarray,
    bin_edges: np.ndarray,
) -> tuple[np.ndarray, int]:
    """Return deterministic class-balanced weights within fixed energy bins.

    Each bin contributes the smaller of its signal and background counts to
    each class. This is the deterministic weighted equivalent of downsampling
    both classes to their common support without discarding random events.
    Bins missing either class receive zero weight.
    """
    checked_labels = np.asarray(labels).reshape(-1)
    checked_energy = np.asarray(energy_sum, dtype=np.float64).reshape(-1)
    edges = np.asarray(bin_edges, dtype=np.float64).reshape(-1)
    if checked_labels.size != checked_energy.size:
        raise ValueError("labels and energy_sum must have equal lengths")
    if edges.size < 2 or not np.all(np.isfinite(edges)):
        raise ValueError("bin_edges must contain at least two finite values")
    if np.any(edges[1:] <= edges[:-1]):
        raise ValueError("bin_edges must be strictly increasing")
    if not np.all(np.isin(checked_labels, (0, 1))):
        raise ValueError("labels must be binary values 0 or 1")
    if not np.all(np.isfinite(checked_energy)):
        raise ValueError("energy_sum must be finite")

    bin_ids = np.searchsorted(edges, checked_energy, side="right") - 1
    bin_ids[checked_energy == edges[-1]] = edges.size - 2
    in_range = (bin_ids >= 0) & (bin_ids < edges.size - 1)
    weights = np.zeros(checked_labels.size, dtype=np.float64)
    common_bins = 0
    for bin_id in np.unique(bin_ids[in_range]):
        in_bin = in_range & (bin_ids == bin_id)
        signal = in_bin & (checked_labels == 1)
        background = in_bin & (checked_labels == 0)
        signal_count = int(np.count_nonzero(signal))
        background_count = int(np.count_nonzero(background))
        common_count = min(signal_count, background_count)
        if common_count == 0:
            continue
        common_bins += 1
        weights[signal] = common_count / signal_count
        weights[background] = common_count / background_count
    return weights, common_bins


def energy_balanced_indices(
    labels: np.ndarray,
    energy_sum: np.ndarray,
    bin_edges: np.ndarray,
) -> EnergyBalancedSelection:
    """Select equal class counts per energy bin without replacement.

    Input order is the deterministic tie breaker. Bins containing only one
    class are excluded. The returned indices are sorted so downstream data
    access remains stable and reproducible.
    """
    checked_labels = np.asarray(labels).reshape(-1)
    checked_energy = np.asarray(energy_sum, dtype=np.float64).reshape(-1)
    edges = np.asarray(bin_edges, dtype=np.float64).reshape(-1)
    if checked_labels.size != checked_energy.size:
        raise ValueError("labels and energy_sum must have equal lengths")
    if edges.size < 2 or not np.all(np.isfinite(edges)):
        raise ValueError("bin_edges must contain at least two finite values")
    if np.any(edges[1:] <= edges[:-1]):
        raise ValueError("bin_edges must be strictly increasing")
    if not np.all(np.isin(checked_labels, (0, 1))):
        raise ValueError("labels must be binary values 0 or 1")
    if not np.all(np.isfinite(checked_energy)):
        raise ValueError("energy_sum must be finite")

    bin_ids = np.searchsorted(edges, checked_energy, side="right") - 1
    bin_ids[checked_energy == edges[-1]] = edges.size - 2
    in_range = (bin_ids >= 0) & (bin_ids < edges.size - 1)
    selected_parts: list[np.ndarray] = []
    common_bins = 0
    selected_per_class = 0
    for bin_id in np.unique(bin_ids[in_range]):
        in_bin = in_range & (bin_ids == bin_id)
        signal = np.flatnonzero(in_bin & (checked_labels == 1))
        background = np.flatnonzero(in_bin & (checked_labels == 0))
        common_count = min(signal.size, background.size)
        if common_count == 0:
            continue
        common_bins += 1
        selected_per_class += common_count
        selected_parts.extend((signal[:common_count], background[:common_count]))
    if not selected_parts:
        raise ValueError("no energy bin contains both classes")
    selected = np.sort(np.concatenate(selected_parts))
    return EnergyBalancedSelection(
        indices=selected,
        common_bins=common_bins,
        selected_signal=selected_per_class,
        selected_background=selected_per_class,
        excluded_events=int(checked_labels.size - selected.size),
    )


def weighted_roc(
    labels: np.ndarray, scores: np.ndarray, weights: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Compute a weighted ROC curve with tied scores handled as one threshold."""
    checked_labels = np.asarray(labels, dtype=np.uint8).reshape(-1)
    checked_scores = np.asarray(scores, dtype=np.float64).reshape(-1)
    checked_weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    if not (checked_labels.size == checked_scores.size == checked_weights.size):
        raise ValueError("labels, scores, and weights must have equal lengths")
    if np.any(checked_weights < 0) or not np.all(np.isfinite(checked_weights)):
        raise ValueError("weights must be finite and non-negative")
    active = checked_weights > 0
    checked_labels = checked_labels[active]
    checked_scores = checked_scores[active]
    checked_weights = checked_weights[active]
    positive_total = float(checked_weights[checked_labels == 1].sum())
    negative_total = float(checked_weights[checked_labels == 0].sum())
    if positive_total <= 0 or negative_total <= 0:
        raise ValueError("weighted ROC requires positive weight for both classes")

    order = np.argsort(-checked_scores, kind="mergesort")
    sorted_scores = checked_scores[order]
    sorted_labels = checked_labels[order]
    sorted_weights = checked_weights[order]
    positive = np.cumsum(sorted_weights * (sorted_labels == 1))
    negative = np.cumsum(sorted_weights * (sorted_labels == 0))
    threshold_indices = np.flatnonzero(
        np.r_[sorted_scores[1:] != sorted_scores[:-1], True]
    )
    true_positive_rate = np.r_[0.0, positive[threshold_indices] / positive_total]
    false_positive_rate = np.r_[0.0, negative[threshold_indices] / negative_total]
    thresholds = np.r_[np.inf, sorted_scores[threshold_indices]]
    auc = float(np.trapezoid(true_positive_rate, false_positive_rate))
    return false_positive_rate, true_positive_rate, thresholds, auc


def energy_matched_roc(
    labels: np.ndarray,
    scores: np.ndarray,
    energy_sum: np.ndarray,
    bin_edges: np.ndarray,
) -> EnergyMatchedRoc:
    """Compute the task's fixed-bin deterministic energy-matched ROC AUC."""
    checked_labels, checked_scores, checked_energy = _validated_vectors(
        labels, scores, energy_sum
    )
    weights, common_bins = energy_matching_weights(
        checked_labels, checked_energy, bin_edges
    )
    false_positive_rate, true_positive_rate, thresholds, auc = weighted_roc(
        checked_labels, checked_scores, weights
    )
    included = weights > 0
    return EnergyMatchedRoc(
        auc=auc,
        false_positive_rate=false_positive_rate,
        true_positive_rate=true_positive_rate,
        thresholds=thresholds,
        event_weights=weights,
        included_events=int(np.count_nonzero(included)),
        excluded_events=int(included.size - np.count_nonzero(included)),
        included_signal=int(np.count_nonzero(included & (checked_labels == 1))),
        included_background=int(np.count_nonzero(included & (checked_labels == 0))),
        common_bins=common_bins,
        total_bins=int(np.asarray(bin_edges).size - 1),
    )
