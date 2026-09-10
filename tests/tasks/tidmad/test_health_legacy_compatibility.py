"""Historical TIDMAD Health compatibility, not current campaign treatment.

The golden is copied byte-for-byte from the framework's pre-08b evidence.
The temporary artifact removes only the subsequently added role field, so
the real resolver must recover membership through the audited SHA map.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from execute_tools.dataset_config import DatasetProfile, bind_dataset_profile
from execute_tools.health_checks.candidate_eligibility import (
    _LEGACY_ROLES_BY_CONFIG_SHA,
    legacy_config_body_sha,
    resolve_scientific_gate_ids,
)
from execute_tools.health_checks.config import load_health_gates_config

GOLDEN = Path(__file__).with_name("goldens") / "pre_08b_shipped_configs.json"
HISTORICAL_SHAS = {
    "observe": "d133a12d3133fb20d632383aa010b1a861fe0fdb6fb6436874b2142d6b5ef58d",
    "blocking": "3b5521180f5460a4a7aa67ad0ff67701633d75ed8fdcac4277c222b713655b74",
}
SCIENTIFIC = frozenset(
    {"output_diversity_blocking", "output_std_blocking", "amplitude_collapse_blocking"}
)


@pytest.mark.parametrize("key", ["observe", "blocking"])
def test_known_historical_roleless_config_is_recovered_by_sha(tmp_path, key):
    captured = json.loads(GOLDEN.read_text())[key]
    body = yaml.safe_load(captured["raw"])
    for gate in body["health_gates"]:
        gate.pop("gate_role", None)
    artifact = tmp_path / f"historical_{key}.yaml"
    artifact.write_text(yaml.safe_dump(body, sort_keys=False))
    path = str(artifact)

    # Historical task_health_peek markers expanded to this audited task roster.
    # No ambient framework profile may supply those indices after separation.
    profile = DatasetProfile(
        partition_count=20,
        topology={},
        anchor_selection_files=[0, 10, 19],
        health_peek_files=[3, 10, 17],
    )
    with bind_dataset_profile(profile):
        assert captured["expected_body_sha256"] == HISTORICAL_SHAS[key]
        assert legacy_config_body_sha(path) == HISTORICAL_SHAS[key]
        assert all(
            gate.gate_role is None
            for gate in load_health_gates_config(path).health_gates
        )
        assert resolve_scientific_gate_ids(path) == SCIENTIFIC


def test_audited_map_keeps_original_sha_keys():
    """Rekeying to current policy hashes would orphan historical workspaces."""
    assert set(_LEGACY_ROLES_BY_CONFIG_SHA) == set(HISTORICAL_SHAS.values())
