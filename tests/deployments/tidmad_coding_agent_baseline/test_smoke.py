from __future__ import annotations

from types import SimpleNamespace

import pytest
from deployments.tidmad_coding_agent_baseline.tools import smoke_test
from deployments.tidmad_coding_agent_baseline.tools.smoke_test import (
    _REQUIRED_RESULTS,
    _verify_results,
)


def _complete_result(root):
    result = root / "result"
    result.mkdir()
    for name in _REQUIRED_RESULTS:
        (result / name).write_bytes(b"ok\n")
    (result / "gpu.txt").write_text("NVIDIA H100 80GB HBM3\n")
    (result / "reload-ok.txt").write_text("CHECKPOINT_RELOAD_OK\n")
    return result


def test_smoke_refuses_a_self_report_without_independent_action_artifacts(tmp_path):
    result = tmp_path / "result"
    result.mkdir()
    (result / "COMPLETE").write_text("everything worked\n")

    with pytest.raises(RuntimeError, match="missing non-empty artifacts"):
        _verify_results(tmp_path)


def test_smoke_requires_h100_evidence_and_checkpoint_reload(tmp_path):
    result = _complete_result(tmp_path)
    (result / "gpu.txt").write_text("No devices were found\n")
    with pytest.raises(RuntimeError, match="does not prove an H100"):
        _verify_results(tmp_path)

    (result / "gpu.txt").write_text("NVIDIA H100 80GB HBM3\n")
    (result / "reload-ok.txt").write_text("failed\n")
    with pytest.raises(RuntimeError, match="does not confirm checkpoint reload"):
        _verify_results(tmp_path)

    (result / "reload-ok.txt").write_text("checkpoint confirmed\n")
    with pytest.raises(RuntimeError, match="does not confirm checkpoint reload"):
        _verify_results(tmp_path)


def test_smoke_runs_product_from_the_declared_smoke_root(tmp_path, monkeypatch):
    observed_cwd = None

    def fake_run(command, **kwargs):
        nonlocal observed_cwd
        if command == ["codex", "--version"]:
            return SimpleNamespace(stdout="codex-cli test\n", returncode=0)
        observed_cwd = kwargs.get("cwd")
        kwargs["stdout"].write(b'{"model":"gpt-5.6-sol"}\n')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(smoke_test.subprocess, "run", fake_run)
    monkeypatch.setattr(smoke_test, "_help_text", lambda _product: "all flags present")
    monkeypatch.setattr(smoke_test, "_required_flags", lambda _product: ())
    monkeypatch.setattr(smoke_test, "_verify_results", lambda _root: {"ok": "digest"})

    root = tmp_path / "smoke"
    smoke_test.smoke("codex", root, "gpt-5[.]6-sol", 10)

    assert observed_cwd == root
    assert "write non-empty confirmation text" in smoke_test.SMOKE_PROMPT
