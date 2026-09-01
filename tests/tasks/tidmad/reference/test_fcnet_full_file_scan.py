"""Task-owned contract tests for the full-file FCNet diagnostic."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tasks.tidmad.tools import fcnet_full_file_scan as scan


def test_paper_geometry_and_band_mapping_remain_exact() -> None:
    """A changed window, batch, or band would no longer reproduce the paper path."""
    assert scan.INPUT_SIZE == 40_000
    assert scan.BATCH_SIZE == 25
    assert scan.BANDS == [(0, 4), (4, 10), (10, 15), (15, 20)]
    assert [scan._band_for_file(index) for index in (0, 3, 4, 9, 10, 14, 15, 19)] == [
        (0, 4),
        (0, 4),
        (4, 10),
        (4, 10),
        (10, 15),
        (10, 15),
        (15, 20),
        (15, 20),
    ]


def test_historical_paths_are_derived_from_explicit_roots() -> None:
    """Filename compatibility must not require one developer's directories."""
    assert scan._model_path(Path("/models"), 10, 15) == Path("/models/FCNet_10_15.pth")
    assert scan._validation_path(Path("/data"), 7) == Path(
        "/data/abra_validation_0007.h5"
    )
    assert scan._output_path(Path("/out"), 7) == Path(
        "/out/abra_validation_denoised_fcnet_0007.h5"
    )


def test_machine_inputs_are_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing or invoking the tool must not select ambient machine paths."""
    monkeypatch.setattr(sys, "argv", ["fcnet-full-file-scan"])

    with pytest.raises(SystemExit) as exc_info:
        scan.main()

    assert exc_info.value.code == 2
