"""Task-owned contract tests for the historical FCNet Health comparison."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tasks.tidmad.tools import fcnet_health_metrics_scan as scan


def test_historical_output_patterns_remain_exact(tmp_path: Path) -> None:
    """A changed literal would make the scanner miss existing artifacts."""
    fcnet = tmp_path / "abra_validation_denoised_fcnet_0000.h5"
    fcnet.touch()
    collapsed = tmp_path / (
        "abra_validation_denoised_wavenet_baseline_wavenet_baseline_wavenet_"
        "1784177030_0000.h5"
    )
    collapsed.touch()

    with pytest.raises(FileNotFoundError, match="Missing 19 input file"):
        scan._paths(tmp_path, "fcnet")
    with pytest.raises(FileNotFoundError, match="Missing 19 input file"):
        scan._paths(tmp_path, "wavenet", "1784177030")


def test_machine_specific_inputs_are_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """No developer path may silently become another machine's evidence."""
    monkeypatch.setattr(sys, "argv", ["fcnet-health-metrics-scan"])

    with pytest.raises(SystemExit) as exc_info:
        scan._args()

    assert exc_info.value.code == 2
