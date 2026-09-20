"""Catch unbound execution limits and fixed-controller leakage in O preparation."""

import json
import shutil
from pathlib import Path

import pytest

from experiments.shared.checksum_manifest import sha256_file
from experiments.tidmad.main_orchestrator.execution_policy import (
    resolve_execution_policy,
)

ROOT = Path(__file__).resolve().parents[2]


def copied_authority(tmp_path):
    rel = Path("experiments/tidmad/main_fixed_workflow/workflow.json")
    raw = json.loads((ROOT / rel).read_text())
    for name in [rel, Path(raw["task_composition"]), Path(raw["agent_parameters"])]:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, tmp_path / name)
    return tmp_path / rel, raw


def test_execution_projection_tracks_authority_changes_without_fixed_topology(tmp_path):
    # Fails if O hardcodes stale caps/budgets or imposes fixed iteration/round limits.
    path, raw = copied_authority(tmp_path)
    for flag, value in {
        "--max_epochs": 73,
        "--trial_max_epochs": 17,
        "--formal_max_epochs": 61,
        "--formal_time_budget_minutes": 19,
        "--num_iterations": 777,
        "--max_rounds": 9,
    }.items():
        raw["parameters"][flag] = value
    path.write_text(json.dumps(raw))
    policy, digest = resolve_execution_policy(tmp_path, ROOT)
    assert (policy.max_epochs, policy.trial_max_epochs, policy.formal_max_epochs) == (
        73,
        17,
        61,
    )
    assert policy.formal_time_budget_minutes == 19
    assert digest == sha256_file(path)
    assert "num_iterations" not in policy.model_dump()
    assert "max_rounds" not in policy.model_dump()


def test_incomplete_execution_authority_cannot_silently_use_native_defaults(tmp_path):
    # Fails if a missing role cap falls back to a framework default after a pin update.
    path, raw = copied_authority(tmp_path)
    del raw["parameters"]["--formal_max_epochs"]
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="explicit execution settings"):
        resolve_execution_policy(tmp_path, ROOT)
