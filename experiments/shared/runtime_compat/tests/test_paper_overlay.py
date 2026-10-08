"""The explicit overlay covers the existing inventory without rewriting it."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_native_paper_unit_retains_its_original_launch_identity():
    original = json.loads(
        (ROOT.parent / "planner_compat/paper-replay-369.json").read_text()
    )["units"]
    overlay = json.loads((ROOT / "paper-measured-completion-v1.json").read_text())
    actual = overlay["covered_units"]
    assert len(actual) == len(original) == 11
    assert len({row["run_id"] for row in actual}) == 11
    assert {
        (row["run_id"], row["historical_infra_revision"], row["launch_sha256"])
        for row in actual
    } == {
        (row["run_id"], row["infra_revision"], row["launch_sha256"]) for row in original
    }
    mapping = {
        "345c802d": "345c802d",
        "7689fd58": "7689fd58",
        "0ab15736": "7689fd58",
        "c0467447": "7689fd58",
        "349b6cd6": "349b6cd6",
    }
    for row in actual:
        family = mapping[row["historical_infra_revision"][:8]]
        assert row["launch_parameters"] == {
            "--runtime_verifier": f"legacy-{family}-verifier-v1"
        }
        late = row["historical_infra_revision"].startswith(("349b6cd6", "c0467447"))
        prefix = "legacy-9b78d505cb11-paper" + ("-late" if late else "")
        assert row["llm_configuration"] == {
            "tune": {"planner_strategy": prefix + "-verifier-v8"}
        }
    assert overlay["launch_parameters"] == {
        "--runtime_completion_policy": "verified-prediction-v1",
        "--trial_time_admission_source": "measured",
        "--formal_time_admission_source": "measured",
    }
