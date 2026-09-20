"""Requests cannot substitute research-owned files for a training completion."""

import json
import os

import pytest
from pydantic import ValidationError

from experiments.shared.validation_admission import (
    ValidationLossRequest,
    admit_validation_loss,
)


@pytest.fixture
def registry(tmp_path):
    root = tmp_path / "trusted"
    root.mkdir(mode=0o700)
    ref = {"logical_ref": "blob", "sha256": "a" * 64, "media_type": "application/json"}
    record = {
        "training_record_id": "train-1",
        "run_id": "run-1",
        "state": "completed",
        "completed_epochs": 1,
        "infra_revision": "b" * 40,
        "task_composition_fingerprint": "c" * 64,
        "model": {
            "artifact_ref": ref,
            "model_artifact_id": "model-1",
            "executable_model_identity_sha256": "d" * 64,
        },
        "objective": ref,
        "objective_review_id": "review-1",
        "validation_scope": ref,
    }
    path = root / "train-1.json"
    path.write_text(json.dumps(record))
    path.chmod(0o600)
    review = {
        "review_id": "review-1",
        "run_id": "run-1",
        "method": "automatic",
        "objective": ref,
        "policy_sha256": "e" * 64,
        "decision": "approved",
        "checks": [
            {
                "stage": stage,
                "passed": True,
                "reason": "synthetic fixture",
                "evidence": ref,
            }
            for stage in ("source", "synthetic", "purpose")
        ],
    }
    review_path = root / "review-1.review.json"
    review_path.write_text(json.dumps(review))
    review_path.chmod(0o600)
    settings = {
        "registry": root,
        "owner_uid": os.getuid(),
        "run_id": "run-1",
        "infra_revision": "b" * 40,
        "task_composition_fingerprint": "c" * 64,
        "review_policy_sha256": "e" * 64,
    }
    return root, path, record, settings


@pytest.mark.parametrize(
    "attack",
    [
        "missing",
        "rejected",
        "objective",
        "policy",
        "run",
        "incomplete",
        "forged_pass",
        "writable",
    ],
)
def test_training_alone_does_not_authorize_an_unreviewed_objective(registry, attack):
    root, _, _, settings = registry
    path = root / "review-1.review.json"
    review = json.loads(path.read_text())
    if attack == "missing":
        path.unlink()
    elif attack == "writable":
        path.chmod(0o666)
    else:
        if attack == "rejected":
            review["decision"] = "rejected"
            review["checks"][0]["passed"] = False
        elif attack == "objective":
            review["objective"]["sha256"] = "f" * 64
        elif attack == "policy":
            review["policy_sha256"] = "f" * 64
        elif attack == "run":
            review["run_id"] = "other"
        elif attack == "incomplete":
            review["checks"].pop()
        else:
            review["checks"][0]["passed"] = False
        path.write_text(json.dumps(review))
    with pytest.raises((ValueError, OSError)):
        admit_validation_loss(
            ValidationLossRequest(training_record_id="train-1"), **settings
        )


def test_admits_matching_completion_without_loading_code(registry):
    _, _, _, settings = registry
    result = admit_validation_loss(
        ValidationLossRequest(training_record_id="train-1"), **settings
    )
    assert result.completed_epochs == 1
    assert result.model.model_artifact_id == "model-1"


@pytest.mark.parametrize(
    "extra", ["model_path", "loss_code", "scope", "targets", "analysis"]
)
def test_rejects_caller_selected_execution_fields(extra):
    with pytest.raises(ValidationError):
        ValidationLossRequest.model_validate(
            {"training_record_id": "train-1", extra: "x"}
        )


@pytest.mark.parametrize("value", ["../train-1", "/tmp/train-1", "a/b", "", "a" * 97])
def test_rejects_paths_in_record_selector(value):
    with pytest.raises(ValidationError):
        ValidationLossRequest(training_record_id=value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("run_id", "other"),
        ("infra_revision", "e" * 40),
        ("task_composition_fingerprint", "f" * 64),
        ("training_record_id", "other"),
        ("state", "running"),
        ("completed_epochs", 0),
        ("completed_epochs", True),
    ],
)
def test_rejects_wrong_identity_or_incomplete_training(registry, field, value):
    _, path, record, settings = registry
    record[field] = value
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        admit_validation_loss(
            ValidationLossRequest(training_record_id="train-1"), **settings
        )


@pytest.mark.parametrize(
    "attack",
    ["writable_record", "writable_root", "symlink", "hardlink", "owner", "missing"],
)
def test_rejects_untrusted_registry_entries(registry, attack):
    root, path, _, settings = registry
    if attack == "writable_record":
        path.chmod(0o666)
    elif attack == "writable_root":
        root.chmod(0o777)
    elif attack in {"symlink", "hardlink"}:
        other = root.parent / "research.json"
        path.rename(other)
        if attack == "symlink":
            path.symlink_to(other)
        else:
            os.link(other, path)
    elif attack == "owner":
        settings["owner_uid"] += 1
    else:
        path.unlink()
    with pytest.raises(OSError):
        admit_validation_loss(
            ValidationLossRequest(training_record_id="train-1"), **settings
        )
