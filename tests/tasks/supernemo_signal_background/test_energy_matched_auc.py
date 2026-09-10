"""Scientific-contract tests for SuperNEMO energy-matched ROC AUC."""

from __future__ import annotations

import numpy as np
import pytest

from tasks.supernemo_signal_background.plugins.energy_matched_auc import (
    energy_balanced_indices,
    energy_matched_roc,
)


def test_energy_matching_removes_bin_population_shortcut() -> None:
    """A score that only identifies an imbalanced energy bin must fall to chance."""
    labels = np.array([1] * 9 + [1] + [0] + [0] * 9)
    energy = np.array([1.5] * 9 + [0.5] + [1.5] + [0.5] * 9)
    scores = (energy > 1.0).astype(float)

    result = energy_matched_roc(labels, scores, energy, np.array([0.0, 1.0, 2.0]))

    assert result.auc == pytest.approx(0.5)
    assert result.common_bins == 2
    assert result.excluded_events == 0


def test_perfect_within_energy_discrimination_remains_perfect() -> None:
    labels = np.array([1, 1, 0, 0, 1, 1, 0, 0])
    energy = np.array([0.2, 0.4, 0.3, 0.5, 1.2, 1.4, 1.3, 1.5])
    scores = labels.astype(float)

    result = energy_matched_roc(labels, scores, energy, np.array([0.0, 1.0, 2.0]))

    assert result.auc == pytest.approx(1.0)


def test_bins_without_both_classes_are_excluded_and_reported() -> None:
    labels = np.array([1, 0, 1])
    energy = np.array([0.2, 0.4, 1.2])
    scores = np.array([0.9, 0.1, 0.8])

    result = energy_matched_roc(labels, scores, energy, np.array([0.0, 1.0, 2.0]))

    assert result.auc == pytest.approx(1.0)
    assert result.common_bins == 1
    assert result.included_events == 2
    assert result.excluded_events == 1


def test_invalid_bin_edges_refuse() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        energy_matched_roc(
            np.array([0, 1]),
            np.array([0.1, 0.9]),
            np.array([1.0, 1.0]),
            np.array([0.0, 1.0, 1.0]),
        )


def test_training_selection_is_exactly_balanced_inside_each_energy_bin() -> None:
    labels = np.array([1, 1, 1, 0, 1, 0, 0, 0, 1])
    energy = np.array([0.2, 0.3, 0.4, 0.5, 1.2, 1.3, 1.4, 1.5, 2.2])
    edges = np.array([0.0, 1.0, 2.0, 3.0])

    result = energy_balanced_indices(labels, energy, edges)

    selected_labels = labels[result.indices]
    selected_energy = energy[result.indices]
    selected_bins = np.searchsorted(edges, selected_energy, side="right") - 1
    for bin_id in np.unique(selected_bins):
        in_bin = selected_bins == bin_id
        assert np.count_nonzero(selected_labels[in_bin] == 1) == np.count_nonzero(
            selected_labels[in_bin] == 0
        )
    assert result.common_bins == 2
    assert result.selected_signal == result.selected_background == 2
    assert result.excluded_events == 5
