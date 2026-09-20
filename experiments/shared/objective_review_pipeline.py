"""One-time automatic objective admission; never call this inside an epoch loop.

The deployment supplies a confined numerical worker and the existing LLM gateway.
The result carries all stage evidence for protected persistence before admission.
No candidate source executes in this coordinator.
"""

import time
from collections.abc import Callable
from typing import Literal

from agent.schemas.data_analysis.common import CertifiedArtifactRef, canonical_sha256
from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

from experiments.shared.objective_numerical_review import (
    NumericalReviewRequest,
    NumericalReviewResult,
)
from experiments.shared.objective_purpose_review import (
    ObjectiveReviewMaterial,
    ReviewGateway,
    review_objective_purpose,
)
from experiments.shared.objective_review import (
    ObjectiveReviewCheck,
    ObjectiveReviewReceipt,
)
from experiments.shared.objective_source_check import inspect_objective_source


class ReviewStageEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    stage: Literal["source", "synthetic", "purpose"]
    payload: dict[str, JsonValue]
    seconds: float


class AutomaticReviewBundle(BaseModel):
    """Persist the complete bundle, not just its approval flag."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    material: ObjectiveReviewMaterial
    numerical_request: NumericalReviewRequest
    receipt: ObjectiveReviewReceipt
    evidence: tuple[ReviewStageEvidence, ...]

    @model_validator(mode="after")
    def verify_integrity(self):
        if self.material.sha256 != self.receipt.objective.sha256:
            raise ValueError("review objective differs from saved material")
        if (
            self.numerical_request.source not in self.material.sources.values()
            or self.numerical_request.parameters != self.material.effective_parameters
        ):
            raise ValueError("numerical source/config differs from reviewed material")
        package = self.numerical_request.code_package
        if package is not None and package.sources != self.material.sources:
            raise ValueError("numerical package differs from reviewed source files")
        if len(self.evidence) != len(self.receipt.checks):
            raise ValueError("review evidence is incomplete")
        for check, item in zip(self.receipt.checks, self.evidence, strict=True):
            if check.stage != item.stage or check.evidence.sha256 != canonical_sha256(
                item
            ):
                raise ValueError("review evidence differs from receipt")
            if (
                check.stage == "synthetic"
                and check.passed
                and item.payload.get("request_sha256")
                != canonical_sha256(self.numerical_request)
            ):
                raise ValueError("numerical evidence belongs to different input")
        return self


def review_objective(
    material: ObjectiveReviewMaterial,
    numerical_request: NumericalReviewRequest,
    *,
    run_id: str,
    review_id: str,
    policy_sha256: str,
    allowed_import_roots: frozenset[str],
    numerical_worker: Callable[[NumericalReviewRequest], NumericalReviewResult],
    gateway: ReviewGateway,
) -> AutomaticReviewBundle:
    """Check exact material in order; earlier refusal skips costly later work.

    A numerical worker must already enforce confinement and timeout. The policy
    identity must include its fixture/dependency configuration and the gateway
    provider/model/settings. The caller persists this evidence under protected
    ownership, then reuses the matching receipt during subsequent epochs.
    """
    material = ObjectiveReviewMaterial.model_validate(material).model_copy(deep=True)
    numerical_request = NumericalReviewRequest.model_validate(
        numerical_request
    ).model_copy(deep=True)
    # The native validator consumes one assembled plugin. Other executable
    # dependencies stay in the reviewed material/runtime; they are not silently
    # assembled or imported by this coordinator.
    if numerical_request.source not in material.sources.values():
        raise ValueError("numerical plugin is absent from reviewed source bundle")
    if (
        numerical_request.code_package is not None
        and numerical_request.code_package.sources != material.sources
    ):
        raise ValueError("numerical package differs from reviewed source files")
    if numerical_request.parameters != material.effective_parameters:
        raise ValueError("numerical parameters differ from reviewed objective")
    objective = CertifiedArtifactRef(
        logical_ref=f"objective/{material.sha256}",
        sha256=material.sha256,
        media_type="application/json",
    )
    checks = []
    evidence = []
    allowed = True
    for stage in ("source", "synthetic", "purpose"):
        started = time.perf_counter()
        passed = False
        payload = {}
        reason = "Skipped because an earlier review stage refused"
        if allowed:
            try:
                if stage == "source":
                    result = inspect_objective_source(
                        material, allowed_import_roots=allowed_import_roots
                    )
                    passed = result.passed
                    reason = (
                        "Source check passed"
                        if passed
                        else "Source contains prohibited or unreviewable operations"
                    )
                elif stage == "synthetic":
                    result = numerical_worker(numerical_request.model_copy(deep=True))
                    if not isinstance(result, NumericalReviewResult):
                        raise TypeError(
                            "numerical worker returned an unvalidated result"
                        )
                    if result.request_sha256 != canonical_sha256(numerical_request):
                        raise ValueError(
                            "numerical result belongs to different material"
                        )
                    passed, reason = result.passed, result.reason
                else:
                    result = review_objective_purpose(material, gateway)
                    passed = result.decision == "approved"
                    reason = result.reason
                payload = result.model_dump(mode="json")
            except Exception as exc:  # noqa: BLE001 - external worker/gateway failures become recorded refusals
                reason = f"Review stage failed: {type(exc).__name__}"
                payload = {"error_type": type(exc).__name__}
        item = ReviewStageEvidence(
            stage=stage,
            payload={**payload, "outcome_reason": reason},
            seconds=time.perf_counter() - started,
        )
        evidence.append(item)
        checks.append(
            ObjectiveReviewCheck(
                stage=stage,
                passed=passed,
                reason=reason,
                evidence=CertifiedArtifactRef(
                    logical_ref=f"review/{review_id}/{stage}",
                    sha256=canonical_sha256(item),
                    media_type="application/json",
                ),
            )
        )
        allowed = allowed and passed
    return AutomaticReviewBundle(
        material=material,
        numerical_request=numerical_request,
        receipt=ObjectiveReviewReceipt(
            method="automatic",
            run_id=run_id,
            review_id=review_id,
            objective=objective,
            policy_sha256=policy_sha256,
            decision="approved" if allowed else "rejected",
            checks=tuple(checks),
        ),
        evidence=tuple(evidence),
    )
