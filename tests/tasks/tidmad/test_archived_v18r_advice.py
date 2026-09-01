"""Task-owned checks for the archived TIDMAD V18r advice artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ADVICE = (
    ROOT / "experiments/tidmad/archived/v18r/architecture_advice.json",
    ROOT / "experiments/tidmad/archived/v18r/loss_advice.json",
)


@pytest.mark.parametrize("path", ADVICE, ids=lambda path: path.name)
def test_no_stale_16_gb_language(path: Path) -> None:
    assert "16 GB" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", ADVICE, ids=lambda path: path.name)
def test_states_the_12_gib_hard_cap(path: Path) -> None:
    body = path.read_text(encoding="utf-8")
    assert "12 GiB" in body
    assert re.search(r"12 GiB (per-chain )?(HARD CAP|hard cap)", body)


@pytest.mark.parametrize("path", ADVICE, ids=lambda path: path.name)
def test_keeps_the_fcnet_reference_with_the_measured_peak(path: Path) -> None:
    body = path.read_text(encoding="utf-8")
    assert "323" in body
    assert "6.04 GiB" in body


@pytest.mark.parametrize("path", ADVICE, ids=lambda path: path.name)
def test_encourages_the_10m_to_100m_range_without_mandating_300m(path: Path) -> None:
    body = path.read_text(encoding="utf-8")
    assert "10M-100M" in body
    assert "must be 323M" not in body
    assert "minimum parameter count" not in body


@pytest.mark.parametrize("path", ADVICE, ids=lambda path: path.name)
def test_is_valid_json_with_the_expected_sections(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"mindset", "propose", "implement", "tune", "validate"}
    assert all(isinstance(value, list) and value for value in data.values())
