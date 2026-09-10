"""Task-owned contract tests for the official-paper Health scanner."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tasks.tidmad.tools import official_paper_health_scan as scan


def test_paper_checkpoint_bands_remain_exact() -> None:
    """Changing a band would attribute a file to the wrong paper checkpoint."""
    assert [scan.band_of(index) for index in range(scan.NUM_FILES)] == [
        "0_4",
        "0_4",
        "0_4",
        "0_4",
        "4_10",
        "4_10",
        "4_10",
        "4_10",
        "4_10",
        "4_10",
        "10_15",
        "10_15",
        "10_15",
        "10_15",
        "10_15",
        "15_20",
        "15_20",
        "15_20",
        "15_20",
        "15_20",
    ]


def test_partial_scan_reports_missing_files(tmp_path: Path) -> None:
    """A partial official run must never be presented as all twenty files."""
    present = tmp_path / "abra_validation_denoised_fcnet_0000.h5"
    present.touch()

    paths, missing = scan.resolve_paths(
        tmp_path,
        "fcnet",
        "abra_validation_denoised_{model}_{index:04d}.h5",
        allow_partial=True,
    )

    assert paths == {0: str(present)}
    assert missing == list(range(1, scan.NUM_FILES))


def test_target_directory_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    """No machine-local TIDMAD directory may silently become evidence."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "official-paper-health-scan",
            "--model",
            "fcnet",
            "--denoised-dir",
            "/tmp/outputs",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        scan.parse_args()

    assert exc_info.value.code == 2
