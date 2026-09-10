"""Task-owned contract tests for the historical Pearson feasibility study."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from tasks.tidmad.tools import investigate_pearson_feasibility as study


def test_historical_case_identity_and_paths_remain_exact(tmp_path: Path) -> None:
    """Catches a case, file cohort, or historical artifact identity drifting."""
    assert study.AGENT_BEST_EXP_ID == "012"
    assert study.AGENT_BEST_FILES == tuple(range(12, 20))
    assert study.FCNET_FILES == (10, 11, 12, 13, 14)
    assert study.agent_best_path(12, directory=tmp_path).name.endswith("012_0012.h5")
    assert study.fcnet_path(14, directory=tmp_path).name == (
        "abra_validation_denoised_fcnet_0014.h5"
    )


def test_metric_bundle_distinguishes_aligned_and_constant_outputs() -> None:
    """Catches the feasibility study dropping alignment or diversity evidence."""
    target = np.array([-2, -1, 0, 1, 2], dtype=np.int8)

    aligned = study.compute_metrics(target, target)
    collapsed = study.compute_metrics(np.zeros_like(target), target)

    assert aligned["pearson"] == pytest.approx(1.0)
    assert aligned["mse_mv2"] == pytest.approx(0.0)
    assert np.isnan(collapsed["pearson"])
    assert collapsed["output_unique_int8_count"] == 1


def test_synthetic_collapse_is_deterministic() -> None:
    """Catches the fixed feasibility comparison losing reproducibility."""
    first = study.synthesize_collapse(0, 0.1, 100, np.random.default_rng(42))
    second = study.synthesize_collapse(0, 0.1, 100, np.random.default_rng(42))

    assert np.array_equal(first, second)
    assert np.count_nonzero(first) <= 10


def test_machine_roots_are_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Catches developer-machine defaults returning to the external tool."""
    monkeypatch.setattr(sys, "argv", ["investigate-pearson-feasibility"])

    with pytest.raises(SystemExit, match="2"):
        study._args()
