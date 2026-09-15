from __future__ import annotations

import json

import pytest
from deployments.tidmad_coding_agent_baseline.tools import finalize as finalize_module
from deployments.tidmad_coding_agent_baseline.tools.archive_candidate import (
    archive_candidate,
    candidate_tree_digest,
)
from deployments.tidmad_coding_agent_baseline.tools.finalize import finalize
from deployments.tidmad_coding_agent_baseline.tools.model import (
    DEVELOPMENT_FILE_BY_BAND,
)


def _source(root, tag):
    root.mkdir()
    (root / "model.py").write_text(f"TAG = {tag!r}\n")
    (root / "architecture.json").write_text(json.dumps({"tag": tag}))
    (root / "train_config.json").write_text(json.dumps({"epochs": 1}))
    (root / "weights.pth").write_bytes(tag.encode())
    (root / "predict.py").write_text("raise SystemExit('test fixture only')\n")
    return root


def _score(path, source, band, scalar):
    vector = [None] * 20
    vector[DEVELOPMENT_FILE_BY_BAND[band]] = scalar
    path.write_text(
        json.dumps(
            {
                "valid": True,
                "scalar": scalar,
                "file_vector": vector,
                "candidate_tree_sha256": candidate_tree_digest(source),
            }
        )
    )
    return path


def test_valid_candidates_are_immutable_and_higher_score_marks_best(tmp_path):
    archive = tmp_path / "state" / "candidates"
    one = _source(tmp_path / "one", "one")
    first = archive_candidate(
        source=one,
        score_path=_score(tmp_path / "one-score.json", one, "0-3", 1.0),
        archive_root=archive,
        band="0-3",
        candidate_id="one",
    )
    two = _source(tmp_path / "two", "two")
    archive_candidate(
        source=two,
        score_path=_score(tmp_path / "two-score.json", two, "0-3", 2.0),
        archive_root=archive,
        band="0-3",
        candidate_id="two",
    )

    assert (first / "COMPLETE.json").is_file()
    assert json.loads((archive / "best" / "0-3.json").read_text())["candidate_id"] == "two"
    with pytest.raises(FileExistsError, match="already published"):
        archive_candidate(
            source=tmp_path / "one",
            score_path=tmp_path / "one-score.json",
            archive_root=archive,
            band="0-3",
            candidate_id="one",
        )


def test_finalizer_collects_partial_results_without_fabricating_score(tmp_path):
    work = tmp_path / "work"
    archive = work / "state" / "candidates"
    candidate = _source(tmp_path / "candidate", "partial")
    archive_candidate(
        source=candidate,
        score_path=_score(tmp_path / "score.json", candidate, "0-3", 1.5),
        archive_root=archive,
        band="0-3",
        candidate_id="partial",
    )

    submission = finalize(
        work,
        "codex",
        archive_root=archive,
        final_score_path=tmp_path / "absent-final-score.json",
    )
    manifest = json.loads((submission / "manifest.json").read_text())

    assert manifest["complete"] is False
    assert manifest["missing_bands"] == ["4-9", "10-14", "15-19"]
    assert not (submission / "score_vector.json").exists()
    assert (submission / "band_0-3" / "weights.pth").is_file()
    assert (submission / "band_0-3" / "score.json").is_file()


def test_archive_refuses_score_with_wrong_band_identities(tmp_path):
    candidate = _source(tmp_path / "candidate", "bad")
    bad = tmp_path / "bad-score.json"
    bad.write_text(
        json.dumps(
            {
                "valid": True,
                "scalar": 1.0,
                "file_vector": [1.0] * 20,
                "candidate_tree_sha256": candidate_tree_digest(candidate),
            }
        )
    )
    with pytest.raises(ValueError, match="differ from frozen holdout"):
        archive_candidate(
            source=candidate,
            score_path=bad,
            archive_root=tmp_path / "archive",
            band="0-3",
            candidate_id="bad",
        )


def test_archive_refuses_score_from_different_candidate_bytes(tmp_path):
    scored = _source(tmp_path / "scored", "scored")
    score = _score(tmp_path / "score.json", scored, "0-3", 1.0)
    submitted = _source(tmp_path / "submitted", "submitted")

    with pytest.raises(ValueError, match="not bound to these candidate bytes"):
        archive_candidate(
            source=submitted,
            score_path=score,
            archive_root=tmp_path / "archive",
            band="0-3",
            candidate_id="mismatch",
        )


def test_finalizer_runs_hidden_final_once_from_four_retained_winners(tmp_path, monkeypatch):
    archive = tmp_path / "state" / "candidates"
    bands = ("0-3", "4-9", "10-14", "15-19")
    for band in bands:
        candidate = _source(tmp_path / f"candidate-{band}", band)
        archive_candidate(
            source=candidate,
            score_path=_score(tmp_path / f"score-{band}.json", candidate, band, 1.0),
            archive_root=archive,
            band=band,
            candidate_id=f"winner-{band}",
        )

    final_score = tmp_path / "state" / "final_score.json"
    calls = []

    def fake_inference(**kwargs):
        calls.append(("inference", sorted(kwargs["winners"])))
        kwargs["output_root"].mkdir(parents=True)
        return kwargs["output_root"]

    def fake_score(args, policy):
        calls.append(("score", sorted(args.winner)))
        policy.final_score.parent.mkdir(parents=True, exist_ok=True)
        policy.final_score.write_text(
            json.dumps(
                {
                    "valid": True,
                    "file_vector": [1.0] * 20,
                    "winner_candidates": {band: f"winner-{band}" for band in bands},
                }
            )
        )
        return policy.final_score

    monkeypatch.setattr(finalize_module, "run_candidate_inference", fake_inference)
    monkeypatch.setattr(finalize_module, "score_final", fake_score)
    submission = finalize_module.finalize(
        tmp_path,
        "codex",
        archive_root=archive,
        final_score_path=final_score,
    )

    assert [name for name, _detail in calls] == ["inference", "score"]
    assert json.loads((submission / "manifest.json").read_text())["complete"] is True


def test_finalizer_records_hidden_failure_without_retrying_or_losing_winners(tmp_path, monkeypatch):
    archive = tmp_path / "state" / "candidates"
    bands = ("0-3", "4-9", "10-14", "15-19")
    for band in bands:
        candidate = _source(tmp_path / f"candidate-{band}", band)
        archive_candidate(
            source=candidate,
            score_path=_score(tmp_path / f"score-{band}.json", candidate, band, 1.0),
            archive_root=archive,
            band=band,
            candidate_id=f"winner-{band}",
        )

    calls = []

    def fail_inference(**_kwargs):
        calls.append("inference")
        raise RuntimeError("predictor failed")

    monkeypatch.setattr(finalize_module, "run_candidate_inference", fail_inference)
    first = finalize_module.finalize(
        tmp_path,
        "claude",
        archive_root=archive,
        final_score_path=tmp_path / "state" / "final_score.json",
    )
    manifest = json.loads((first / "manifest.json").read_text())
    assert manifest["complete"] is False
    assert manifest["missing_bands"] == []
    assert manifest["final_evaluation_attempted"] is True
    assert manifest["final_evaluation_failure"]["error_type"] == "RuntimeError"
    assert calls == ["inference"]

    # A second finalizer invocation must not query the hidden set again.
    finalize_module.finalize(
        tmp_path / "second-finalizer",
        "claude",
        archive_root=archive,
        final_score_path=tmp_path / "state" / "final_score.json",
    )
    assert calls == ["inference"]
