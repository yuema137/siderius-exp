"""Scientific metric checks for Majorana energy matching."""

from __future__ import annotations

import numpy as np
import pytest

from tasks.majorana_low_avse.plugins._majorana_metrics import (
    _energy_weights,
    _weighted_auc,
)


def test_energy_matching_removes_spectrum_only_separation() -> None:
    """A score encoding only an imbalanced energy spectrum must fall to chance."""
    labels = np.array([0] * 9 + [1] + [0] + [1] * 9, dtype=np.uint8)
    energies = np.array([10.0] * 10 + [30.0] * 10)
    scores = np.array([0.0] * 10 + [1.0] * 10)

    ordinary = _weighted_auc(labels, scores, np.ones(labels.size))
    matched = _weighted_auc(labels, scores, _energy_weights(labels, energies))

    assert ordinary == pytest.approx(0.9)
    assert matched == pytest.approx(0.5)
