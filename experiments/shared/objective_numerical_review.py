"""Synthetic objective check entrypoint; launch only inside an isolated worker.

The caller supplies task-owned tiny numeric fixtures, never real samples. This
module does not establish isolation or authorize private validation. It reuses
SIDERIUS's numerical validator with the effective objective parameters.
"""

from __future__ import annotations

import math
import os
import sys
import time
from typing import Annotated, Literal

from agent.schemas.custom_loss_contract import CustomLossApplicability
from agent.schemas.custom_loss_validation import validate_custom_loss_plugin
from agent.schemas.data_analysis.common import Sha256, canonical_sha256
from agent.schemas.model_io_contract import ModelIOContract, TensorContract
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    JsonValue,
    StrictBool,
    StrictInt,
    model_validator,
)

from experiments.shared.objective_code_package import (
    ObjectiveCodePackage,
    bound_objective_source,
    require_package_source,
)


class SyntheticTensor(BaseModel):
    """Bounded plain numeric fixture; no pickle, device or executable payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    shape: tuple[Annotated[StrictInt, Field(gt=0, le=4096)], ...] = Field(max_length=8)
    dtype: Literal["float32", "float64", "int64"]
    values: tuple[StrictInt | FiniteFloat, ...] = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def check_geometry(self):
        if math.prod(self.shape) != len(self.values):
            raise ValueError("synthetic tensor shape differs from supplied values")
        if self.dtype == "int64" and any(type(v) is not int for v in self.values):
            raise ValueError("integer fixture requires integer values without casting")
        return self

    def tensor(self):
        import torch

        return torch.tensor(self.values, dtype=getattr(torch, self.dtype)).reshape(
            self.shape
        )


class NumericalReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: str = Field(min_length=1, max_length=1048576)
    loss_name: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,95}$")
    parameters: dict[str, JsonValue]
    prediction: SyntheticTensor
    target: SyntheticTensor
    model_io: ModelIOContract | None = None
    supervision_target: TensorContract | None = None
    applicability: CustomLossApplicability | None = None
    code_package: ObjectiveCodePackage | None = None

    @model_validator(mode="after")
    def matching_source(self):
        require_package_source(self.source, self.code_package)
        return self


class NumericalReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    request_sha256: Sha256
    passed: StrictBool
    reason: str = Field(min_length=1)
    seconds: Annotated[FiniteFloat, Field(ge=0)]


def check_numerically(request: NumericalReviewRequest) -> NumericalReviewResult:
    """Execute candidate source here only when this process is already confined."""
    request = NumericalReviewRequest.model_validate(request).model_copy(deep=True)
    identity = canonical_sha256(request)
    started = time.perf_counter()
    with bound_objective_source(request.source, request.code_package) as path:
        error = validate_custom_loss_plugin(
            request.source,
            request.loss_name,
            plugin_path=str(path) if request.code_package is not None else None,
            model_io=request.model_io,
            supervision_target=request.supervision_target,
            applicability=request.applicability,
            pair_provider=lambda: (
                request.prediction.tensor(),
                request.target.tensor(),
            ),
            loss_parameters=request.parameters,
        )
    return NumericalReviewResult(
        request_sha256=identity,
        passed=error is None,
        reason=error
        or "Finite scalar and finite prediction gradients on supplied synthetic fixtures",
        seconds=time.perf_counter() - started,
    )


def main() -> None:
    payload = sys.stdin.buffer.read(2097153)
    if len(payload) > 2097152:
        raise ValueError("numerical review request exceeds limit")
    request = NumericalReviewRequest.model_validate_json(payload)
    # Ordinary candidate stdout must not corrupt the structured reply. The
    # launcher owns stderr, confinement and timeout; this is not a sandbox.
    sys.stdout.flush()
    reply_fd = os.dup(sys.stdout.fileno())
    try:
        os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
        result = check_numerically(request)
        sys.stdout.flush()
    finally:
        os.dup2(reply_fd, sys.stdout.fileno())
        os.close(reply_fd)
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
