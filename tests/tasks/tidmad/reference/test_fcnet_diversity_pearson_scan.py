"""Task-owned tests for the historical FCNet diversity diagnostic."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from tasks.tidmad.tools import fcnet_diversity_pearson_scan as scan


def test_historical_artifact_paths_remain_exact(tmp_path: Path) -> None:
    """Catches a current producer template replacing historical replay names."""
    primary = tmp_path / "primary"
    fallback = tmp_path / "fallback"
    primary.mkdir()
    fallback.mkdir()
    fallback_file = fallback / "abra_validation_denoised_fcnet_0014.h5"
    fallback_file.touch()

    assert (
        scan.fcnet_path(14, primary_dir=primary, fallback_dir=fallback) == fallback_file
    )
    assert scan.baseline_path(3, directory=tmp_path, exp_id="1784177030").name == (
        "abra_validation_denoised_wavenet_baseline_wavenet_baseline_wavenet_"
        "1784177030_0003.h5"
    )


def test_pearson_preserves_alignment_and_constant_output_semantics() -> None:
    """Catches the diagnostic ceasing to distinguish aligned and collapsed output."""
    target = np.array([-2, -1, 0, 1, 2], dtype=np.int8)

    assert scan.compute_pearson(target, target) == pytest.approx(1.0)
    assert np.isnan(scan.compute_pearson(np.zeros_like(target), target))


def test_machine_roots_are_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Catches a developer-specific filesystem default returning to the tool."""
    monkeypatch.setattr(sys, "argv", ["fcnet-diversity-pearson-scan"])

    with pytest.raises(SystemExit, match="2"):
        scan._args()
