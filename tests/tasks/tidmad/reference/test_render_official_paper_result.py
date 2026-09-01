"""Task-owned tests for deterministic official-paper result rendering."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tasks.tidmad.tools import render_official_paper_result as render


def _summary() -> dict:
    return {
        "model_key": "fcnet",
        "model": "TIDMAD official band-split FCNet",
        "file_vector_linear": [5.27],
        "file_vector_log": [1.0],
        "checkpoint_by_file": {"0": "0_4"},
        "inference_seconds": {"0": 2.5},
        "denoising_score": 6.4348,
        "full_scope": True,
        "file_indices": [0],
        "seg_size": 40_000,
        "batch_size": 1,
        "device": "cuda:0",
        "s_max": 295_715_680.14,
        "computed_at": "2026-01-01T00:00:00Z",
        "data_dir": "/external/data",
    }


def test_summary_filename_contract_is_preserved(tmp_path: Path) -> None:
    """A renamed input would make an existing paper score disappear."""
    expected = tmp_path / "tidmad_official_fcnet_banded_score.json"
    expected.write_text(json.dumps(_summary()), encoding="utf-8")

    assert render.load_summary(tmp_path, "fcnet") == _summary()
    assert render.load_summary(tmp_path, "punet") is None


def test_per_model_report_preserves_the_scientific_ruler(tmp_path: Path) -> None:
    """The renderer must not change the frozen score or aggregation statement."""
    output = tmp_path / "fcnet.md"

    render.render_per_model(_summary(), output)

    text = output.read_text(encoding="utf-8")
    assert "Canonical `denoising_score` = 6.434800" in text
    assert "log_5.27" in text
    assert "raw-baseline floor = 1.0007" in text
    assert "ground-truth ceiling = 10.1134" in text
    assert "Per-band or per-subset aggregates are NOT reported" in text


def test_input_and_output_directories_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rendering must not read from or write to an ambient repository path."""
    monkeypatch.setattr(sys, "argv", ["render-official-paper-result"])

    with pytest.raises(SystemExit) as exc_info:
        render.parse_args()

    assert exc_info.value.code == 2
