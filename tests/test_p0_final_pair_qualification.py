"""Deterministic contracts for final consumer-pair wrapper boundaries."""

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WRAPPERS = sorted((ROOT / "experiments").glob("*/p0_final_pair_qualification/launch.sh"))


@pytest.mark.parametrize("wrapper", WRAPPERS)
def test_wrapper_rejects_unknown_arguments(wrapper: Path) -> None:
    result = subprocess.run(["bash", str(wrapper), "--unknown"], capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "unknown argument" in result.stderr


@pytest.mark.parametrize("wrapper", WRAPPERS)
def test_wrapper_help_is_available(wrapper: Path) -> None:
    result = subprocess.run(["bash", str(wrapper), "--help"], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert "--siderius-checkout" in result.stdout
