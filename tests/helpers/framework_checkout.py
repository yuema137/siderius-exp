"""Explicit pinned source resources for installed-package consumer tests."""

import os
import subprocess
from pathlib import Path

EXP_ROOT = Path(__file__).resolve().parents[2]


def pinned_framework_checkout() -> Path:
    """Refuse absent or mismatched source instead of borrowing another checkout."""
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    assert configured, "SIDERIUS_CHECKOUT must name the exact framework pin"
    root = Path(configured).resolve()
    expected = (EXP_ROOT / "SIDERIUS_REVISION").read_text().strip()
    actual = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert actual == expected, "SIDERIUS_CHECKOUT disagrees with the exp pin"
    return root


def framework_health_policy() -> str:
    """Use the real pinned policy; never a synthetic replacement for Gold."""
    path = pinned_framework_checkout() / "configs" / "health" / "health_checks.yaml"
    assert path.is_file(), f"pinned framework Health policy missing: {path}"
    return str(path)


def framework_source_path(module_name: str) -> Path:
    """Resolve an independently selected module source under the pinned src tree."""
    relative = Path(*module_name.split(".")).with_suffix(".py")
    path = pinned_framework_checkout() / "src" / relative
    assert path.is_file(), f"pinned framework module source missing: {path}"
    return path
