"""Original evaluator facts retain scope, identity and ineligibility semantics."""

import json
import os

import pytest

from experiments.tidmad.main_orchestrator.baseline_receipt import (
    read_baseline_evaluation,
)


def _receipt(tmp_path, **changes):
    payload = {
        "scalar": 1.5,
        "file_vector": [1.0, 2.0, 1.0, 2.0] + [None] * 16,
        "scoreable": True,
        "valid": False,
        "evaluation_split": "official-validation",
        "evaluation_scope": "complete-band",
        "candidate_tree_sha256": "a" * 64,
        "run_id": "smoke",
        "invocation_id": "one",
        "health_status": "invalid",
        "health_passed": False,
        "health_gate_results": [],
        "health_effective_config_sha256": "b" * 64,
        "eligible_for_selection": False,
    }
    payload.update(changes)
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(payload))
    path.chmod(0o440)
    return path


def _read(path, **changes):
    expected = {
        "band": "0-3",
        "candidate_sha256": "a" * 64,
        "run_id": "smoke",
        "invocation_id": "one",
        "owner_uid": os.getuid(),
    }
    expected.update(changes)
    return read_baseline_evaluation(path, **expected)


def test_complete_but_ineligible_evaluation_preserves_feedback(tmp_path):
    receipt = _read(_receipt(tmp_path))
    assert receipt.scalar == 1.5 and receipt.scoreable
    assert not receipt.eligible_for_selection and not receipt.valid


@pytest.mark.parametrize(
    "fault",
    ["candidate", "invocation", "band", "partial", "health", "writable", "link"],
)
def test_unrelated_partial_or_inconsistent_evidence_is_refused(tmp_path, fault):
    changes = {}
    if fault == "partial":
        changes["file_vector"] = [1.0] + [None] * 19
    if fault == "health":
        changes["eligible_for_selection"] = True
    path = _receipt(tmp_path, **changes)
    expected = {}
    if fault == "candidate":
        expected["candidate_sha256"] = "c" * 64
    if fault == "invocation":
        expected["invocation_id"] = "old"
    if fault == "band":
        expected["band"] = "4-9"
    if fault == "writable":
        path.chmod(0o660)
    if fault == "link":
        link = tmp_path / "link"
        link.symlink_to(path)
        path = link
    with pytest.raises((ValueError, OSError)):
        _read(path, **expected)


def test_original_nonfinite_refusal_is_feedback_not_transport_failure(tmp_path):
    receipt = _read(_receipt(tmp_path, scalar=float("-inf"), scoreable=False))
    assert not receipt.scoreable and receipt.scalar == float("-inf")
    other = tmp_path / "scoreable"
    other.mkdir()
    with pytest.raises(ValueError, match="finite score"):
        _read(_receipt(other, scalar=float("nan")))
