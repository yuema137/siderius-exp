"""Require one SIDERIUS revision for experiment source, lock, and execution."""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
from importlib.metadata import distribution
from pathlib import Path

_SHA = re.compile(r"[0-9a-f]{40}\Z")


def verify_framework_pin(repository_root: Path, checkout: Path) -> str:
    """Return the exact revision, refusing mixed source and dependency pins."""

    for repository in (repository_root, checkout):
        status = subprocess.run(
            ["git", "-C", str(repository), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if status:
            raise ValueError(f"launch checkout has uncommitted files: {repository}")
    expected = (repository_root / "SIDERIUS_REVISION").read_text(encoding="utf-8").strip()
    if _SHA.fullmatch(expected) is None:
        raise ValueError("SIDERIUS_REVISION must contain one full Git SHA")
    project = tomllib.loads((repository_root / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = [
        item.rsplit("@", 1)[1]
        for item in project["project"]["dependencies"]
        if item.startswith("siderius @ ")
    ]
    if dependencies != [expected]:
        raise ValueError("pyproject.toml SIDERIUS dependency differs from SIDERIUS_REVISION")
    lock = tomllib.loads((repository_root / "uv.lock").read_text(encoding="utf-8"))
    packages = [item for item in lock["package"] if item["name"] == "siderius"]
    if len(packages) != 1 or packages[0]["source"]["git"].rsplit("#", 1)[-1] != expected:
        raise ValueError("uv.lock SIDERIUS revision differs from SIDERIUS_REVISION")
    actual = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual != expected:
        raise ValueError(f"SIDERIUS checkout revision differs from SIDERIUS_REVISION: {actual}")
    return expected


def verify_installed_framework(expected: str) -> None:
    """Require this exp virtualenv's installed SIDERIUS package to match."""

    direct_url = distribution("siderius").read_text("direct_url.json")
    installed = json.loads(direct_url or "{}").get("vcs_info", {}).get("commit_id")
    if installed != expected:
        raise ValueError("installed SIDERIUS revision differs from SIDERIUS_REVISION")
