"""Native review reuse must bind actual defaults and avoid parallel duplicate calls."""

import fcntl
import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from agent.schemas.data_analysis.common import canonical_sha256

from experiments.shared.native_objective_metadata import NativeObjectiveMetadata
from experiments.shared.objective_numerical_review import (
    NumericalReviewRequest,
    NumericalReviewResult,
)
from experiments.shared.objective_purpose_review import ObjectiveReviewMaterial
from experiments.shared.validation_admission import review_native_objective_once


def inputs():
    source = "import torch\n# synthetic source for review persistence only\n"
    material = ObjectiveReviewMaterial(
        sources={"loss.py": source},
        effective_parameters={"scale": 2.0},
        dependency_declaration="synthetic runtime",
    )
    request = NumericalReviewRequest(
        source=source,
        loss_name="fixture",
        parameters={"scale": 2.0},
        prediction={"shape": [1], "dtype": "float32", "values": [0.0]},
        target={"shape": [1], "dtype": "float32", "values": [1.0]},
    )
    metadata = NativeObjectiveMetadata(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        loss_name="fixture",
        effective_parameters={"scale": 2.0},
        target_dtype="float",
        reduction="mean",
    )
    return material, request, metadata


@pytest.mark.parametrize("approved", [True, False])
def test_parallel_review_reuses_complete_evidence_and_rejection(tmp_path, approved):
    calls = []

    class Gateway:
        def generate(self, *args, **kwargs):
            calls.append("purpose")
            return {
                "decision": "approved" if approved else "rejected",
                "reason": "synthetic verdict",
            }

    def numerical(request):
        calls.append("numerical")
        return NumericalReviewResult(
            request_sha256=canonical_sha256(request),
            passed=True,
            reason="synthetic fixture",
            seconds=0.0,
        )

    def review(_, deadline=None):
        return review_native_objective_once(
            *inputs(),
            registry=tmp_path,
            owner_uid=os.getuid(),
            run_id="run",
            policy_sha256="a" * 64,
            allowed_import_roots=frozenset({"torch"}),
            numerical_worker=numerical,
            gateway=Gateway(),
            deadline=deadline,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(review, range(4)))
    assert calls == ["numerical", "purpose"]
    assert all(item == results[0] for item in results)
    assert results[0].receipt.decision == ("approved" if approved else "rejected")
    # A separate open-file description models another concurrent invocation.
    with (tmp_path / f"{results[0].receipt.review_id}.lock").open("rb") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        started = time.monotonic()
        with pytest.raises(TimeoutError, match="review lock deadline"):
            review(None, deadline=started + 0.05)
        assert time.monotonic() - started < 1
    assert calls == ["numerical", "purpose"]
    # Recover a crash after evidence publication but before the receipt write.
    (tmp_path / f"{results[0].receipt.review_id}.review.json").unlink()
    assert review(None) == results[0]
    assert calls == ["numerical", "purpose"]


def test_changed_native_defaults_refuse_before_review_or_registry_write(tmp_path):
    material, request, metadata = inputs()
    metadata = metadata.model_copy(update={"effective_parameters": {"scale": 3.0}})
    with pytest.raises(ValueError, match="native objective source/defaults"):
        review_native_objective_once(
            material,
            request,
            metadata,
            registry=tmp_path,
            owner_uid=os.getuid(),
            run_id="run",
            policy_sha256="a" * 64,
            allowed_import_roots=frozenset({"torch"}),
            numerical_worker=None,
            gateway=None,
        )
    assert list(tmp_path.iterdir()) == []
