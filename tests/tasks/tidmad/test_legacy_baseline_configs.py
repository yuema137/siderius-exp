"""Ownership and byte-parity checks for the TIDMAD baseline configurations."""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINES = (
    REPO_ROOT / "tasks" / "tidmad" / "reference_data" / "legacy_baseline_configs.json"
)
IMPORTED_SHA256 = "2e15932ae8c87500b888f95efb4f356f16ed646a2f42b144fafd9610163728b0"


def test_imported_baseline_config_bytes_are_preserved() -> None:
    """The ownership move must not alter any published baseline value."""
    assert hashlib.sha256(BASELINES.read_bytes()).hexdigest() == IMPORTED_SHA256


def test_baseline_consumers_use_the_task_owned_artifact() -> None:
    """Task tools must not reach back into the framework for scientific config."""
    consumers = (
        REPO_ROOT / "tasks" / "tidmad" / "tools" / "run_comparison.py",
    )
    for consumer in consumers:
        source = consumer.read_text(encoding="utf-8")
        assert '"ml_models" / "legacy_baseline_configs.json"' not in source
        assert '"ml_models", "legacy_baseline_configs.json"' not in source
        assert "reference_data" in source
        assert "legacy_baseline_configs.json" in source
