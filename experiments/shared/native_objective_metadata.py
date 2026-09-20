"""Resolve native custom-loss defaults in a target-free, confined worker.

Run once when assembling automatic review, not per epoch. Importing candidate
source can execute code: the launcher must establish isolation before this CLI.
Returned metadata is evidence to bind to captured source, not review approval.
"""

import hashlib
import os
import sys
from typing import Literal

from agent.schemas.data_analysis.common import Sha256
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from experiments.shared.objective_code_package import (
    ObjectiveCodePackage,
    bound_objective_source,
    require_package_source,
)


class ObjectiveMetadataRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: str = Field(min_length=1, max_length=1048576)
    loss_name: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,95}$")

    code_package: ObjectiveCodePackage | None = None

    @model_validator(mode="after")
    def matching_source(self):
        require_package_source(self.source, self.code_package)
        return self


class NativeObjectiveMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    package_sha256: Sha256 | None = None
    source_sha256: Sha256
    loss_name: str
    effective_parameters: dict[str, JsonValue]
    target_dtype: Literal["long", "float"]
    reduction: Literal["mean", "sum"] | None


def resolve_native_objective_metadata(
    request: ObjectiveMetadataRequest,
) -> NativeObjectiveMetadata:
    """Use the same plugin loader and Config() defaults as native training."""
    from ml_models.loss_plugin_loader import load_loss_plugin_from_path

    with bound_objective_source(request.source, request.code_package) as path:
        plugin = load_loss_plugin_from_path(str(path))
        if plugin is None or plugin["loss_type"] != request.loss_name:
            raise ValueError("custom objective identity differs from requested source")
        config = plugin["config_class"]()
        if not isinstance(config, BaseModel):
            raise TypeError("native objective configuration must be a Pydantic model")
        return NativeObjectiveMetadata(
            package_sha256=request.code_package.sha256
            if request.code_package
            else None,
            source_sha256=hashlib.sha256(request.source.encode()).hexdigest(),
            loss_name=plugin["loss_type"],
            effective_parameters=config.model_dump(mode="json"),
            target_dtype=plugin["target_dtype"],
            reduction=plugin["reduction"],
        )


def main() -> None:
    payload = sys.stdin.buffer.read(2097153)
    if len(payload) > 2097152:
        raise ValueError("objective metadata request exceeds limit")
    request = ObjectiveMetadataRequest.model_validate_json(payload)
    reply_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    try:
        result = resolve_native_objective_metadata(request)
        with os.fdopen(reply_fd, "w") as reply:
            reply_fd = -1
            reply.write(result.model_dump_json() + "\n")
    finally:
        if reply_fd >= 0:
            os.close(reply_fd)


if __name__ == "__main__":
    main()
