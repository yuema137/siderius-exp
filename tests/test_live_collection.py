"""Exercise repository-level collection, including its real module imports."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

EXP_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("external_cwd", [False, True])
def test_default_collection_keeps_live_tasks_and_excludes_archive(
    tmp_path, external_cwd
):
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTEST_ADDOPTS", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-c",
        str(EXP_ROOT / "pyproject.toml"),
        "--collect-only",
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    # pytest resolves an invocation outside rootdir from the caller's cwd;
    # -c selects configuration, not a directory to search for tests.
    if external_cwd:
        command.append(str(EXP_ROOT / "tests"))
    result = subprocess.run(
        command,
        cwd=tmp_path if external_cwd else EXP_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr
    node_ids = [line for line in result.stdout.splitlines() if "::" in line]
    assert node_ids, result.stdout
    assert len(node_ids) == len(set(node_ids))
    assert not any("provenance/" in node for node in node_ids)
    for path in (
        "tests/tasks/oxford_iiit_pet/test_package_contract.py",
        "tests/tasks/supernemo_signal_background/test_package_contract.py",
        "tests/campaigns/tidmad_gold/stage3/test_strict_best.py",
    ):
        assert any(path + "::" in node for node in node_ids), path
