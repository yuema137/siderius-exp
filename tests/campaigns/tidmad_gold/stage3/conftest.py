"""Hermetic runtime inputs shared by Gold Stage-3 tests."""

from pathlib import Path

import pytest

import campaigns.tidmad_gold.stage3.stage3_common as stage3_common


@pytest.fixture(autouse=True)
def explicit_tidmad_data_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Bind the explicit task data root required by the Stage-3 scorer."""
    data_root = tmp_path / "tidmad_data"
    data_root.mkdir()
    monkeypatch.setattr(stage3_common, "TIDMAD_DATA_DIR", str(data_root))
    return data_root
