"""Read the coordinator-owned scoring receipt without importing the scorer.

A transport boundary, not a second scoring or Health implementation. The
caller side reads what `tess-score` wrote, checks it belongs to this exact
candidate and invocation, and projects it; it never recomputes R² or Health.

Shape follows TIDMAD's `baseline_receipt.py`. What differs is the evidence
geometry: TIDMAD carries a 20-position file vector, TESS carries one scalar
over one evaluated split, so coverage is checked by row count against the
declared population rather than by band membership.
"""

from __future__ import annotations

import math
import os
import stat
from pathlib import Path
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StrictInt,
    model_validator,
)

__all__ = ["TessEvaluationReceipt", "read_tess_evaluation"]

_RECEIPT_LIMIT = 4194304


class TessEvaluationReceipt(BaseModel):
    """What `tess-score` writes. Extra keys are tolerated, required ones are not."""

    model_config = ConfigDict(extra="allow", frozen=True)

    version: Literal["phyts-tess-orchestration-score-v1"]
    scalar: float | None
    scoreable: StrictBool
    valid: StrictBool
    evaluation_split: Literal["val"]
    evaluation_scope: Literal["complete-split"]
    evaluated_rows: StrictInt = Field(gt=0)
    declared_rows: StrictInt = Field(gt=0)
    candidate_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_id: str = Field(min_length=1)
    invocation_id: str = Field(min_length=1)
    health_status: str = Field(min_length=1)
    health_passed: StrictBool
    health_gate_results: tuple[dict[str, JsonValue], ...]
    health_effective_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    eligible_for_selection: StrictBool
    secondary_results: tuple[dict[str, JsonValue], ...] = ()

    @model_validator(mode="after")
    def consistent_eligibility(self) -> Self:
        if self.eligible_for_selection != (self.scoreable and self.health_passed):
            raise ValueError(
                "evaluator eligibility disagrees with scoring/Health evidence"
            )
        if self.valid != self.eligible_for_selection:
            raise ValueError("evaluator validity disagrees with eligibility")
        if self.scoreable and (self.scalar is None or not math.isfinite(self.scalar)):
            raise ValueError("scoreable evaluation omitted a finite score")
        if self.scoreable and self.evaluated_rows != self.declared_rows:
            raise ValueError(
                "scoreable evaluation did not cover the complete declared split"
            )
        return self


def read_tess_evaluation(
    path: Path,
    *,
    candidate_sha256: str,
    run_id: str,
    invocation_id: str,
    owner_uid: int,
) -> TessEvaluationReceipt:
    """Accept bounded coordinator-owned feedback bound to this exact invocation.

    The caller must resolve `path` from the completed scorer's own output;
    this reader is not an authorization endpoint for arbitrary files. No
    task input, prediction or target array is opened here.
    """
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != owner_uid
            or info.st_mode & 0o022
        ):
            raise PermissionError(
                "evaluation receipt must be coordinator-owned and immutable to research"
            )
        payload = stream.read(_RECEIPT_LIMIT + 1)
    if len(payload) > _RECEIPT_LIMIT:
        raise ValueError("evaluation receipt exceeds size limit")

    receipt = TessEvaluationReceipt.model_validate_json(payload)
    if (receipt.candidate_tree_sha256, receipt.run_id, receipt.invocation_id) != (
        candidate_sha256,
        run_id,
        invocation_id,
    ):
        raise ValueError(
            "evaluation receipt belongs to different candidate bytes or invocation"
        )
    return receipt
