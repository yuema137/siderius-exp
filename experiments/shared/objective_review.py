"""Evidence contract for automatic private-validation objective review.

This schema records review, not a proof of confidentiality. The trusted review
worker must perform the checks and retain evidence before publishing a receipt.
"""

from typing import Annotated, Literal

from agent.schemas.data_analysis.common import CertifiedArtifactRef, NonEmptyStr, Sha256
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator


class ObjectiveReviewCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    stage: Literal["source", "synthetic", "purpose"]
    passed: StrictBool
    reason: NonEmptyStr
    evidence: CertifiedArtifactRef


class ObjectiveReviewReceipt(BaseModel):
    """Bind exact code/dependency/parameter bundle to all required checks."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    review_id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}$")]
    run_id: NonEmptyStr
    method: Literal["automatic"]
    objective: CertifiedArtifactRef
    policy_sha256: Sha256
    decision: Literal["approved", "rejected"]
    checks: tuple[ObjectiveReviewCheck, ...]

    @model_validator(mode="after")
    def consistent_decision(self):
        stages = [check.stage for check in self.checks]
        if len(stages) != 3 or set(stages) != {"source", "synthetic", "purpose"}:
            raise ValueError("review requires exactly one result from each stage")
        approved = all(check.passed for check in self.checks)
        if (self.decision == "approved") != approved:
            raise ValueError("review decision disagrees with its check evidence")
        return self
