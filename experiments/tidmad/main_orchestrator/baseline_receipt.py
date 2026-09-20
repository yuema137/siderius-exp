"""Read the existing baseline evaluator's feedback without importing its scorer.

This is a task-side transport boundary, not an alternative scoring or Health
implementation. An ineligible candidate can still have a completed evaluation.
"""

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
    model_validator,
)

from deployments.tidmad_coding_agent_baseline.tools.model import FILES_BY_BAND


class BaselineEvaluationReceipt(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    scalar: float | None
    file_vector: tuple[float | None, ...] = Field(min_length=20, max_length=20)
    scoreable: StrictBool
    valid: StrictBool
    evaluation_split: Literal["official-validation"]
    evaluation_scope: Literal["complete-band"]
    candidate_tree_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_id: str = Field(min_length=1)
    invocation_id: str = Field(min_length=1)
    health_status: str = Field(min_length=1)
    health_passed: StrictBool
    health_gate_results: tuple[dict[str, JsonValue], ...]
    health_effective_config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    eligible_for_selection: StrictBool

    @model_validator(mode="after")
    def consistent_eligibility(self) -> Self:
        if self.eligible_for_selection != (self.scoreable and self.health_passed):
            raise ValueError(
                "evaluator eligibility disagrees with scoring/Health evidence"
            )
        if self.valid != self.eligible_for_selection:
            raise ValueError("evaluator validity disagrees with eligibility")
        if self.scoreable and (
            self.scalar is None
            or not math.isfinite(self.scalar)
            or any(
                value is not None and not math.isfinite(value)
                for value in self.file_vector
            )
        ):
            raise ValueError("scoreable evaluation omitted finite score evidence")
        return self


def read_baseline_evaluation(
    path: Path,
    *,
    band: str,
    candidate_sha256: str,
    run_id: str,
    invocation_id: str,
    owner_uid: int = 0,
) -> BaselineEvaluationReceipt:
    """Accept bounded evaluator-owned feedback bound to this exact invocation.

    The operator supplies the expected evaluator UID (root in the existing
    installation). The caller must resolve the path from the completed scorer's
    output, never use this reader as an authorization endpoint for arbitrary jobs.
    No task inputs, predictions or target arrays are opened here.
    """
    if band not in FILES_BY_BAND:
        raise ValueError("unknown frozen band")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != owner_uid
            or info.st_mode & 0o022
        ):
            raise PermissionError(
                "evaluation receipt must be evaluator-owned and immutable to research"
            )
        payload = stream.read(4194305)
    if len(payload) > 4194304:
        raise ValueError("evaluation receipt exceeds size limit")
    receipt = BaselineEvaluationReceipt.model_validate_json(payload)
    if (receipt.candidate_tree_sha256, receipt.run_id, receipt.invocation_id) != (
        candidate_sha256,
        run_id,
        invocation_id,
    ):
        raise ValueError(
            "evaluation receipt belongs to different candidate bytes or invocation"
        )
    present = {
        index for index, value in enumerate(receipt.file_vector) if value is not None
    }
    expected = set(FILES_BY_BAND[band])
    if not present <= expected or (receipt.scoreable and present != expected):
        raise ValueError("evaluation receipt does not cover the frozen complete band")
    return receipt
