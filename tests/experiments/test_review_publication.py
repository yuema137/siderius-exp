"""Review evidence publication cannot overwrite a different review or publish partial approval."""

import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from experiments.shared.objective_numerical_review import NumericalReviewRequest
from experiments.shared.objective_purpose_review import ObjectiveReviewMaterial
from experiments.shared.objective_review_pipeline import review_objective
from experiments.shared.validation_admission import publish_automatic_review


def rejected_bundle():
    source = "print('refused before execution')"
    material = ObjectiveReviewMaterial(
        sources={"loss.py": source},
        effective_parameters={},
        dependency_declaration="fixture",
    )
    request = NumericalReviewRequest(
        source=source,
        loss_name="fixture",
        parameters={},
        prediction={"shape": [1], "dtype": "float32", "values": [0.0]},
        target={"shape": [1], "dtype": "float32", "values": [1.0]},
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("refused source reached execution")

    return review_objective(
        material,
        request,
        run_id="run-1",
        review_id="review-1",
        policy_sha256="a" * 64,
        allowed_import_roots=frozenset(),
        numerical_worker=forbidden,
        gateway=None,
    )


def test_parallel_identical_publications_preserve_complete_evidence(tmp_path):
    bundle = rejected_bundle()

    def publish(_):
        publish_automatic_review(bundle, registry=tmp_path, owner_uid=os.getuid())

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(publish, range(8)))
    evidence = json.loads((tmp_path / "review-1.evidence.json").read_text())
    receipt = json.loads((tmp_path / "review-1.review.json").read_text())
    assert evidence["receipt"] == receipt
    assert receipt["decision"] == "rejected"
    assert (
        evidence["material"]["sources"]["loss.py"]
        == "print('refused before execution')"
    )
    assert len(list(tmp_path.iterdir())) == 2
    assert (tmp_path / "review-1.review.json").stat().st_mode & 0o077 == 0


def test_conflicting_id_does_not_replace_evidence_or_receipt(tmp_path):
    original = rejected_bundle()
    publish_automatic_review(original, registry=tmp_path, owner_uid=os.getuid())
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    changed = original.model_copy(deep=True)
    changed.receipt.checks[0].evidence.__dict__["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="evidence differs"):
        publish_automatic_review(changed, registry=tmp_path, owner_uid=os.getuid())
    changed = original.model_copy(
        update={
            "receipt": original.receipt.model_copy(update={"run_id": "another-run"})
        }
    )
    with pytest.raises(FileExistsError):
        publish_automatic_review(changed, registry=tmp_path, owner_uid=os.getuid())
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_interrupted_evidence_write_never_publishes_receipt(tmp_path, monkeypatch):
    original = os.rename

    def fail(*args, **kwargs):
        if str(args[1]).endswith(".evidence.json"):
            raise OSError("simulated interrupted publication")
        return original(*args, **kwargs)

    monkeypatch.setattr(os, "rename", fail)
    with pytest.raises(OSError, match="interrupted"):
        publish_automatic_review(
            rejected_bundle(), registry=tmp_path, owner_uid=os.getuid()
        )
    assert not list(tmp_path.iterdir())


def test_publication_lock_respects_remaining_deadline_without_partial_write(tmp_path):
    import fcntl
    import time

    descriptor = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        started = time.monotonic()
        with pytest.raises(TimeoutError, match="review lock deadline"):
            publish_automatic_review(
                rejected_bundle(),
                registry=tmp_path,
                owner_uid=os.getuid(),
                deadline=started + 0.05,
            )
        assert time.monotonic() - started < 1
        assert list(tmp_path.iterdir()) == []
    finally:
        os.close(descriptor)
