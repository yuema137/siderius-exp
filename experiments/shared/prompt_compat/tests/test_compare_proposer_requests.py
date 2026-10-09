"""The baseline must be the recorded pre-fix revision, not any convenient tree."""

import importlib.util
from pathlib import Path

import pytest


def test_wrong_reference_refused_before_capture_or_output(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "compare_proposer_requests.py"
    spec = importlib.util.spec_from_file_location("request_compare", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module.subprocess, "check_output", lambda *a, **k: "wrong-revision\n"
    )
    output = tmp_path / "report"
    with pytest.raises(ValueError, match="pre-fix source revision"):
        module.compare(tmp_path / "reference", tmp_path / "candidate", output)
    assert not output.exists()
