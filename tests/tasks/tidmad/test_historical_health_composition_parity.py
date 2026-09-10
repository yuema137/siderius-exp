"""Preserved Health migration oracles, never current campaign treatment.

The two immutable JSON captures describe distinct historical policies:
pre-C5 any-pass and post-C2 all-pass. Their own captured input declarations
are loaded explicitly; neither config is a default for current campaigns.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from execute_tools.health_checks import _plugin_binding
from execute_tools.health_checks.config import load_composed_health_config

GOLDENS = Path(__file__).with_name("goldens")


@pytest.fixture(autouse=True)
def isolated_scope():
    _plugin_binding.reset_run_scope()
    yield
    _plugin_binding.reset_run_scope()


def _compose(policy: str, task: str):
    composed, _, _ = load_composed_health_config(
        str(GOLDENS / policy), str(GOLDENS / task)
    )
    return composed


def test_post_c2_resolved_config_matches_complete_hc1_capture():
    expected = json.loads((GOLDENS / "hc1_health_checks_resolved.json").read_text())
    expected.pop("_captured_at")
    config = _compose(
        "hc1_framework_policy_f8ef0276.yaml", "hc1_task_health_f8ef0276.yaml"
    )
    assert config.model_dump(mode="json") == expected


def test_pre_c5_executed_semantics_match_original_capture():
    expected = json.loads(
        (GOLDENS / "pre_c5_tidmad_executed_semantics.json").read_text()
    )["gates"]
    # The original migration test (13e28796) compared executed fields, not
    # the capture's reason_sha metadata; it never specified that hash codec.
    # HC1 above separately protects full reason text for its later vintage.
    expected = [
        {key: value for key, value in row.items() if key != "reason_sha"}
        for row in expected
    ]
    config = _compose(
        "p4_framework_health_policy_d44f6f6a.yaml",
        "p4_tidmad_task_health_d44f6f6a.yaml",
    )
    actual = []
    for gate in config.health_gates:
        row = gate.model_dump(mode="json")
        row["on_pass"] = row["on_pass"]["action"]
        row["on_fail"] = row["on_fail"]["action"]
        row.pop("reason")
        # C5 moved the formerly implicit physical unit into task declarations.
        # The pre-C5 capture predates these equivalent explicit fields.
        for check in row["checks"]:
            check["config"].pop("value_scale_units_per_sample", None)
            check["config"].pop("value_scale_unit", None)
        actual.append(row)
    assert actual == expected
