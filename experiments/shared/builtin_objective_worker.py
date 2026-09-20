"""Restore a framework-owned objective in an already-confined numeric worker.

Only installed native builtins are allowed. Custom losses must use the reviewed
objective worker. The protected launcher binds loss settings and source identity
to the actual training invocation; these hashes alone are not authorization.
"""

import hashlib
import inspect
import os
import sys
import time
from pathlib import Path
from typing import Annotated, Self

import torch
from agent.schemas.data_analysis.common import Sha256
from ml_models.models_format_sandbox import LossConfig
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictBool,
    StrictInt,
    model_validator,
)

from experiments.shared.validation_snapshot import load_worker_snapshot


class BuiltinObjectiveWorkerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    loss: LossConfig
    source_sha256: Sha256
    state_fd: Annotated[StrictInt, Field(ge=0)]
    max_snapshot_bytes: Annotated[StrictInt, Field(gt=0)]
    training: StrictBool
    device: str = Field(pattern=r"^(cpu|cuda:[0-9]+)$")
    deadline_epoch: FiniteFloat
    max_frame_bytes: Annotated[StrictInt, Field(ge=1024)]

    @model_validator(mode="after")
    def builtin_only(self) -> Self:
        if self.loss.loss_type == "custom":
            raise ValueError("custom objective requires reviewed worker admission")
        return self


def restore_builtin_objective(config: BuiltinObjectiveWorkerConfig) -> torch.nn.Module:
    from ml_models.loss_models_sandbox import get_criterion

    source = Path(inspect.getfile(get_criterion))
    if hashlib.sha256(source.read_bytes()).hexdigest() != config.source_sha256:
        raise ValueError("native objective source differs from admitted runtime")
    state = load_worker_snapshot(config.state_fd, max_bytes=config.max_snapshot_bytes)
    # Native constructors register an optional buffer only when weights exist.
    # Reconstruct that structure before strict state loading; never drop weights.
    weight_key = {"ce": "weight", "focal_cw": "class_weights"}.get(
        config.loss.loss_type
    )
    weights = state.get(weight_key) if weight_key is not None else None
    objective = get_criterion(config.loss, class_weights=weights).to(
        torch.device(config.device)
    )
    objective.load_state_dict(state, strict=True)
    objective.train(config.training)
    return objective


def main() -> int:
    from experiments.shared.validation_worker_config import read_worker_config

    config = BuiltinObjectiveWorkerConfig.model_validate_json(
        read_worker_config(description=__doc__)
    )
    deadline = time.monotonic() + max(0.0, config.deadline_epoch - time.time())
    if time.monotonic() >= deadline:
        return 1
    reply_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    try:
        from experiments.shared.validation_module_worker import serve_module

        try:
            objective = restore_builtin_objective(config)
        finally:
            os.close(config.state_fd)
        return serve_module(
            objective,
            role="objective",
            device=torch.device(config.device),
            input_fd=sys.stdin.fileno(),
            output_fd=reply_fd,
            deadline=deadline,
            max_frame_bytes=config.max_frame_bytes,
        )
    finally:
        os.close(reply_fd)


if __name__ == "__main__":
    raise SystemExit(main())
