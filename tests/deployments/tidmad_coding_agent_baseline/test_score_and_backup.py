from __future__ import annotations

import argparse
import json
import subprocess

import pytest

from deployments.tidmad_coding_agent_baseline.tools import backup_completed, score
from deployments.tidmad_coding_agent_baseline.tools.evaluator_policy import (
    EvaluatorPolicy,
)


def _candidate_args(tmp_path):
    source = tmp_path / "agent" / "source"
    source.mkdir(parents=True)
    (source / "model.py").write_text("MODEL = 'test'\n")
    (source / "architecture.json").write_text(json.dumps({"kind": "test"}))
    (source / "train_config.json").write_text(json.dumps({"epochs": 1}))
    (source / "weights.pth").write_bytes(b"weights")
    (tmp_path / "agent" / "denoised").mkdir()
    return argparse.Namespace(
        denoised_dir=tmp_path / "agent" / "denoised",
        scope="band-0-3",
        workers=1,
        candidate_source=source,
        band="0-3",
        candidate_id="candidate-1",
    )


def _policy(tmp_path):
    scope_root = tmp_path / "scopes"
    scope_root.mkdir(parents=True)
    (scope_root / "band-0-3.json").write_text('{"0":[0],"1":[0],"2":[0],"3":[0]}')
    return EvaluatorPolicy(
        input_root=tmp_path / "input",
        scope_root=scope_root,
        raw_data_dir=tmp_path / "raw",
        agent_root=tmp_path / "agent",
        archive_root=tmp_path / "state" / "candidates",
        final_score=tmp_path / "state" / "final_score.json",
    )


def test_candidate_scoring_deletes_deliverables_only_after_durable_archive(
    tmp_path, monkeypatch
):
    args = _candidate_args(tmp_path)
    deliverable = tmp_path / "denoised.h5"
    deliverable.write_bytes(b"temporary")
    events = []

    monkeypatch.setattr(
        score,
        "compute_score",
        lambda **_kwargs: (
            {"valid": True, "scalar": 1.0, "file_vector": [1.0] * 4 + [None] * 16},
            [deliverable],
        ),
    )

    def archive(**kwargs):
        assert deliverable.exists()
        assert kwargs["score_path"].exists()
        events.append("archive")
        return tmp_path / "published"

    monkeypatch.setattr(score, "archive_candidate", archive)
    assert score.score_candidate(args, _policy(tmp_path)) == tmp_path / "published"
    assert events == ["archive"]
    assert not deliverable.exists()


def test_candidate_scoring_keeps_deliverables_when_archive_fails(tmp_path, monkeypatch):
    args = _candidate_args(tmp_path)
    deliverable = tmp_path / "denoised.h5"
    deliverable.write_bytes(b"temporary")
    monkeypatch.setattr(
        score,
        "compute_score",
        lambda **_kwargs: (
            {"valid": True, "scalar": 1.0, "file_vector": [1.0] * 4 + [None] * 16},
            [deliverable],
        ),
    )
    monkeypatch.setattr(
        score,
        "archive_candidate",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("archive failed")),
    )
    with pytest.raises(RuntimeError, match="archive failed"):
        score.score_candidate(args, _policy(tmp_path))
    assert deliverable.exists()


def test_privileged_scorer_refuses_agent_selected_scientific_roots(tmp_path):
    args = _candidate_args(tmp_path)
    args.candidate_source = tmp_path / "outside" / "candidate"
    args.candidate_source.mkdir(parents=True)

    with pytest.raises(ValueError, match="candidate source must remain below"):
        score.score_candidate(args, _policy(tmp_path))


def test_privileged_snapshot_never_follows_agent_symlinks(tmp_path, monkeypatch):
    args = _candidate_args(tmp_path)
    hidden = tmp_path / "private-validation"
    hidden.mkdir()
    (hidden / "truth.h5").write_bytes(b"hidden truth")
    (args.candidate_source / "borrowed-truth").symlink_to(
        hidden, target_is_directory=True
    )
    monkeypatch.setattr(
        score,
        "compute_score",
        lambda **_kwargs: pytest.fail("invalid snapshot reached the scorer"),
    )

    with pytest.raises(ValueError, match="contains a symlink"):
        score.score_candidate(args, _policy(tmp_path))


def test_backup_uses_conditional_create_and_records_completed_candidate(
    tmp_path, monkeypatch
):
    candidate = tmp_path / "candidates" / "0-3" / "candidate-1"
    candidate.mkdir(parents=True)
    (candidate / "candidate_manifest.json").write_text('{"candidate_id":"candidate-1"}')
    (candidate / "COMPLETE.json").write_text('{"complete":true}')
    calls = []

    def fake_aws(*args, timeout_seconds):
        calls.append((args, timeout_seconds))
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(backup_completed, "_aws", fake_aws)
    outcomes = backup_completed.backup_completed(
        tmp_path / "candidates",
        bucket="condition-only",
        prefix="codex",
        receipts=tmp_path / "receipts",
        timeout_seconds=42,
    )

    assert outcomes == [(candidate, "created")]
    assert "--if-none-match" in calls[0][0]
    assert calls[0][0][calls[0][0].index("--if-none-match") + 1] == "*"
    assert calls[0][1] == 42
    assert backup_completed.backup_completed(
        tmp_path / "candidates",
        bucket="condition-only",
        prefix="codex",
        receipts=tmp_path / "receipts",
        timeout_seconds=42,
    ) == [(candidate, "already-recorded")]
    assert len(calls) == 1


def test_backup_refuses_preexisting_object_with_different_candidate_identity(
    tmp_path, monkeypatch
):
    candidate = tmp_path / "candidates" / "0-3" / "candidate-1"
    candidate.mkdir(parents=True)
    (candidate / "candidate_manifest.json").write_text('{"candidate_id":"candidate-1"}')
    (candidate / "COMPLETE.json").write_text('{"complete":true}')

    def fake_aws(*args, timeout_seconds):
        if args[1] == "put-object":
            return subprocess.CompletedProcess(args, 1, "", "PreconditionFailed 412")
        return subprocess.CompletedProcess(
            args,
            0,
            '{"Metadata":{"candidate-manifest-sha256":"different"}}',
            "",
        )

    monkeypatch.setattr(backup_completed, "_aws", fake_aws)
    with pytest.raises(RuntimeError, match="different candidate identity"):
        backup_completed.backup_completed(
            tmp_path / "candidates",
            bucket="condition-only",
            prefix="codex",
            receipts=tmp_path / "receipts",
            timeout_seconds=42,
        )
