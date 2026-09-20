"""Admission never skips a required stage or spends later calls after refusal."""

import pytest
from agent.schemas.data_analysis.common import canonical_sha256

from experiments.shared.objective_numerical_review import (
    NumericalReviewRequest,
    NumericalReviewResult,
)
from experiments.shared.objective_purpose_review import ObjectiveReviewMaterial
from experiments.shared.objective_review_pipeline import review_objective


def requests(source="def loss(p,t): return ((p-t)**2).mean()"):
    material = ObjectiveReviewMaterial(
        sources={"loss.py": source},
        effective_parameters={},
        dependency_declaration="synthetic pinned runtime",
    )
    numeric = NumericalReviewRequest(
        source=source,
        loss_name="fixture",
        parameters={},
        prediction={"shape": [1], "dtype": "float32", "values": [0.0]},
        target={"shape": [1], "dtype": "float32", "values": [1.0]},
    )
    return material, numeric


@pytest.mark.parametrize(
    "failure", [None, "source", "numeric_identity", "timeout", "purpose"]
)
def test_stages_bind_evidence_and_stop_after_refusal(failure):
    calls = []
    material, numeric = requests(
        "print('forbidden')"
        if failure == "source"
        else "def loss(p,t): return ((p-t)**2).mean()"
    )

    def worker(request):
        calls.append("synthetic")
        if failure == "timeout":
            raise TimeoutError("worker timed out")
        return NumericalReviewResult(
            request_sha256="0" * 64
            if failure == "numeric_identity"
            else canonical_sha256(request),
            passed=True,
            reason="synthetic witness",
            seconds=0.01,
        )

    class Gateway:
        def generate(self, *args, **kwargs):
            calls.append("purpose")
            return {
                "decision": "rejected" if failure == "purpose" else "approved",
                "reason": "synthetic gateway witness",
            }

    bundle = review_objective(
        material,
        numeric,
        run_id="run-1",
        review_id="review-1",
        policy_sha256="a" * 64,
        allowed_import_roots=frozenset(),
        numerical_worker=worker,
        gateway=Gateway(),
    )
    assert bundle.receipt.decision == ("approved" if failure is None else "rejected")
    expected = (
        []
        if failure == "source"
        else ["synthetic"]
        if failure in {"numeric_identity", "timeout"}
        else ["synthetic", "purpose"]
    )
    assert calls == expected
    assert bundle.receipt.objective.sha256 == material.sha256
    for check, item in zip(bundle.receipt.checks, bundle.evidence, strict=True):
        assert check.evidence.sha256 == canonical_sha256(item)
    if failure in {"source", "numeric_identity", "timeout"}:
        assert bundle.receipt.checks[-1].reason.startswith("Skipped")


@pytest.mark.parametrize(
    "field,value", [("source", "different source"), ("parameters", {"beta": 1.0})]
)
def test_different_numerical_material_refuses_before_any_effect(field, value):
    material, numeric = requests()
    numeric = numeric.model_copy(update={field: value})

    def forbidden(*args, **kwargs):
        raise AssertionError("mismatched material reached execution")

    with pytest.raises(ValueError, match="reviewed"):
        review_objective(
            material,
            numeric,
            run_id="run-1",
            review_id="review-1",
            policy_sha256="a" * 64,
            allowed_import_roots=frozenset(),
            numerical_worker=forbidden,
            gateway=None,
        )


def test_unreviewed_package_helper_refuses_before_any_effect():
    from experiments.shared.objective_code_package import ObjectiveCodePackage

    material, numeric = requests()
    package = ObjectiveCodePackage(
        entrypoint="loss.py",
        sources={**material.sources, "helper.py": "def error(p,t): return p-t"},
    )
    numeric = numeric.model_copy(update={"code_package": package})

    def forbidden(*args, **kwargs):
        raise AssertionError("unreviewed helper reached execution")

    with pytest.raises(ValueError, match="package differs"):
        review_objective(
            material,
            numeric,
            run_id="run-1",
            review_id="review-1",
            policy_sha256="a" * 64,
            allowed_import_roots=frozenset(),
            numerical_worker=forbidden,
            gateway=None,
        )
