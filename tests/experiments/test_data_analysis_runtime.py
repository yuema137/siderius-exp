"""Readiness checks execute the native sandbox, not a command-existence guess."""

import json
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from experiments.shared import data_analysis_runtime as runtime


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "framework with spaces"
    python = root / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    return root


def receipt(checkout, **fields):
    return json.dumps(
        {
            "python_prefix": str(checkout / ".venv"),
            "sandbox": {
                "available": True,
                "protocol_id": "siderius.generated-analysis-sandbox.v1",
                "bubblewrap_path": "/usr/bin/bwrap",
                "unshare_path": "/usr/bin/unshare",
                "reason": None,
                **fields,
            },
        }
    )


def test_probe_binds_exact_framework_python_and_runs_native_authority(
    checkout, monkeypatch
):
    def run(command, **kwargs):
        assert command[:4] == [str(checkout / ".venv/bin/python"), "-I", "-B", "-c"]
        assert "AnalysisCodeSandbox().probe()" in command[4]
        assert kwargs["cwd"] == checkout and kwargs["timeout"] == 20
        return subprocess.CompletedProcess(command, 0, receipt(checkout), "")

    monkeypatch.setattr(runtime.subprocess, "run", run)
    assert (
        runtime.require_generated_analysis_runtime(checkout).sandbox.available is True
    )


@pytest.mark.parametrize(
    "reason",
    [
        "bubblewrap and unshare are both required",
        "unshare: Operation not permitted",
        "numpy import failed",
    ],
)
def test_missing_tools_or_unusable_sandbox_refuse(checkout, monkeypatch, reason):
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a, 0, receipt(checkout, available=False, reason=reason), ""
        ),
    )
    with pytest.raises(ValueError, match="generated-code runtime is unavailable"):
        runtime.require_generated_analysis_runtime(checkout)


@pytest.mark.parametrize(
    "output", ["not JSON", "{}", '{"python_prefix":"/foreign","sandbox":{}}']
)
def test_invalid_receipt_cannot_qualify(checkout, monkeypatch, output):
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, output, ""),
    )
    with pytest.raises(ValidationError):
        runtime.require_generated_analysis_runtime(checkout)


def test_foreign_environment_cannot_qualify(checkout, monkeypatch):
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a, 0, receipt(Path("/foreign")), ""
        ),
    )
    with pytest.raises(ValueError, match="foreign framework environment"):
        runtime.require_generated_analysis_runtime(checkout)


def test_missing_environment_does_not_use_ambient_python(tmp_path, monkeypatch):
    monkeypatch.setattr(
        runtime.subprocess, "run", lambda *a, **k: pytest.fail("ambient fallback")
    )
    with pytest.raises(ValueError, match="environment is missing"):
        runtime.require_generated_analysis_runtime(tmp_path)


@pytest.mark.parametrize("failure", ["timeout", "nonzero"])
def test_worker_failure_is_not_a_pass(checkout, monkeypatch, failure):
    def run(*args, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args[0], 20)
        return subprocess.CompletedProcess(
            args[0], 1, receipt(checkout), "import error"
        )

    monkeypatch.setattr(runtime.subprocess, "run", run)
    with pytest.raises(ValueError, match="qualification"):
        runtime.require_generated_analysis_runtime(checkout)
