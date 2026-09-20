"""Construct approved objective code only inside an already-confined worker.

Do not import/construct candidate losses in a private-data coordinator. The
launcher supplies a protected review bundle and exact numeric epoch state; this
function neither certifies that state nor establishes operating-system isolation.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Self

import torch
from agent.schemas.data_analysis.common import Sha256
from ml_models.loss_plugin_loader import load_loss_plugin_from_path
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictBool,
    StrictInt,
    model_validator,
)

from experiments.shared.objective_code_package import bound_objective_source
from experiments.shared.objective_review_pipeline import AutomaticReviewBundle


def restore_reviewed_objective(
    bundle: AutomaticReviewBundle,
    *,
    expected_policy_sha256: str,
    expected_objective_sha256: str,
    state: Mapping[str, torch.Tensor],
    training: bool,
    device: torch.device,
) -> torch.nn.Module:
    """Reconstruct from approved source/config; never load a pickled module.

    State is the native epoch criterion state, supplied by the trusted execution
    path as plain tensors. Empty state must be explicit. Only run this function
    after mounting the reviewed runtime and confining the worker. Model training
    provenance and review-file ownership are checked by the caller before launch.
    """
    bundle = AutomaticReviewBundle.model_validate_json(bundle.model_dump_json())
    receipt = bundle.receipt
    if (
        receipt.decision != "approved"
        or receipt.policy_sha256 != expected_policy_sha256
        or receipt.objective.sha256 != expected_objective_sha256
        or bundle.material.sha256 != expected_objective_sha256
    ):
        raise ValueError("objective does not have the required approval")
    request = bundle.numerical_request
    if any(type(value) is not torch.Tensor for value in state.values()):
        raise TypeError("objective state requires plain numeric tensors")
    with bound_objective_source(request.source, request.code_package) as source:
        plugin = load_loss_plugin_from_path(str(source))
        if plugin is None or plugin["loss_type"] != request.loss_name:
            raise ValueError("reviewed plugin identity could not be loaded")
        config = plugin["config_class"](**request.parameters)
        objective = plugin["loss_class"](config).to(device)
        objective.load_state_dict(dict(state), strict=True)
        objective.train(training)
        return objective


class ObjectiveWorkerConfig(BaseModel):
    """Trusted launcher configuration; never accept this from a loss request."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    bundle: Path
    state: Path | None = None
    state_fd: Annotated[StrictInt, Field(ge=0)] | None = None
    policy_sha256: Sha256
    objective_sha256: Sha256
    training: StrictBool
    device: str = Field(pattern=r"^(cpu|cuda:[0-9]+)$")
    deadline_epoch: FiniteFloat
    max_frame_bytes: Annotated[StrictInt, Field(ge=1024)]

    @model_validator(mode="after")
    def one_state_source(self) -> Self:
        if (self.state is None) == (self.state_fd is None):
            raise ValueError("objective requires exactly one state source")
        return self


def main() -> int:
    import os
    import sys
    import time

    from pydantic import TypeAdapter

    from experiments.shared.validation_module_protocol import TensorPayload
    from experiments.shared.validation_module_worker import serve_module
    from experiments.shared.validation_snapshot import load_worker_snapshot
    from experiments.shared.validation_worker_config import read_worker_config

    config = ObjectiveWorkerConfig.model_validate_json(
        read_worker_config(description=__doc__)
    )
    deadline = time.monotonic() + max(0.0, config.deadline_epoch - time.time())
    if time.monotonic() >= deadline:
        return 1
    with config.bundle.open("rb") as stream:
        payload = stream.read(4194305)
    if len(payload) > 4194304:
        raise ValueError("objective evidence bundle exceeds limit")
    bundle = AutomaticReviewBundle.model_validate_json(payload)
    reply_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    try:
        if config.state_fd is not None:
            try:
                state = load_worker_snapshot(
                    config.state_fd, max_bytes=config.max_frame_bytes
                )
            finally:
                os.close(config.state_fd)
        else:
            assert config.state is not None
            with config.state.open("rb") as stream:
                payload = stream.read(config.max_frame_bytes + 1)
            if len(payload) > config.max_frame_bytes:
                raise ValueError("objective state exceeds limit")
            encoded = TypeAdapter(dict[str, TensorPayload]).validate_json(payload)
            state = {
                name: item.tensor(device=torch.device("cpu"))
                for name, item in encoded.items()
            }
        objective = restore_reviewed_objective(
            bundle,
            expected_policy_sha256=config.policy_sha256,
            expected_objective_sha256=config.objective_sha256,
            state=state,
            training=config.training,
            device=torch.device(config.device),
        )
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
