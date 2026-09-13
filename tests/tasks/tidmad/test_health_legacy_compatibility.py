"""Retired historical Health inputs refuse without rewriting captured evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from execute_tools.dataset_config import DatasetProfile, bind_dataset_profile
from execute_tools.health_checks.candidate_eligibility import (
    resolve_scientific_gate_ids,
)
from execute_tools.health_checks.config import load_health_gates_config

GOLDEN = Path(__file__).with_name("goldens") / "pre_08b_shipped_configs.json"


@pytest.mark.parametrize("key", ["observe", "blocking"])
def test_captured_historical_marker_refuses_even_with_bound_profile(tmp_path, key):
    """Catch restoration of profile-based marker expansion in the actual reader."""
    captured = json.loads(GOLDEN.read_text())[key]
    artifact = tmp_path / f"historical_{key}.yaml"
    artifact.write_text(captured["raw"], encoding="utf-8")
    path = str(artifact)

    # The formerly sufficient profile must not rescue the obsolete marker.
    profile = DatasetProfile(
        partition_count=20,
        topology={},
        anchor_selection_files=[0, 10, 19],
        health_peek_files=[3, 10, 17],
    )
    with (
        bind_dataset_profile(profile),
        pytest.raises(ValueError, match="peek_file_indices.*explicit list"),
    ):
        load_health_gates_config(path)


def test_roleless_concrete_policy_is_not_rescued_by_historical_membership(tmp_path):
    """Catch accepting missing roles independently of the obsolete-marker refusal."""
    artifact = tmp_path / "roleless.yaml"
    artifact.write_text(
        yaml.safe_dump(
            {
                "health_gates": [
                    {
                        "id": "amplitude_collapse_blocking",
                        "after_round": "every",
                        "checks": [
                            {
                                "name": "amplitude_collapse",
                                "config": {"peek_file_indices": [2, 7]},
                            }
                        ],
                        "on_pass": {"action": "continue"},
                        "on_fail": {"action": "invalidate_round"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert resolve_scientific_gate_ids(str(artifact)) is None
