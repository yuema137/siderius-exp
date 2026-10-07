"""An absent fixture bundle must not produce a successful empty report."""

import importlib.util
from pathlib import Path

import pytest


def test_missing_fixtures_refuse_before_git_or_output(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "compare.py"
    spec = importlib.util.spec_from_file_location("prompt_compare", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "__file__", str(tmp_path / "compare.py"))
    output = tmp_path / "report"
    with pytest.raises(ValueError, match="empty comparison is not qualification"):
        module.compare(tmp_path / "nonexistent-infra", {}, output)
    assert not output.exists()
