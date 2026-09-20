"""Observe native model selection inside a confined, target-free fresh process.

The launcher supplies only captured plugin roots/package transport in the
probe environment. Returned selection is evidence to check against that capture,
not authority to read an arbitrary path or execute code in the coordinator.
"""

import hashlib
import os
import sys
from pathlib import Path

from agent.schemas.data_analysis.common import Sha256
from pydantic import BaseModel, ConfigDict, Field


class ModelDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model_type: str = Field(min_length=1)


class NativeModelSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model_type: str
    constructor_sha256: Sha256
    source_sha256: Sha256
    plugin_path: Path | None


def discover_model(request: ModelDiscoveryRequest) -> NativeModelSelection:
    # Import only after confinement and stdout separation; this import performs
    # the installed native scan, including its existing ordering/selection rules.
    from ml_models import models_sandbox
    from ml_models.plugin_loader import registered_model_plugin_path

    model = models_sandbox.MODEL_REGISTRY.get(request.model_type)
    if model is None:
        raise ValueError("requested model is absent from native registry")
    origin = registered_model_plugin_path(request.model_type, model)
    if origin is None:
        if model.__module__ != models_sandbox.__name__:
            raise ValueError("native model has no recorded plugin origin")
        source = Path(models_sandbox.__file__)
    else:
        source = Path(origin)
    with source.open("rb") as stream:
        payload = stream.read(4194305)
    if len(payload) > 4194304:
        raise ValueError("native model declaration exceeds limit")
    return NativeModelSelection(
        model_type=request.model_type,
        constructor_sha256=models_sandbox.registered_model_construction_implementation_sha256(),
        source_sha256=hashlib.sha256(payload).hexdigest(),
        plugin_path=Path(origin) if origin else None,
    )


def main() -> None:
    payload = sys.stdin.buffer.read(65537)
    if len(payload) > 65536:
        raise ValueError("model discovery request exceeds limit")
    request = ModelDiscoveryRequest.model_validate_json(payload)
    reply_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    try:
        result = discover_model(request)
        with os.fdopen(reply_fd, "w") as reply:
            reply_fd = -1
            reply.write(result.model_dump_json() + "\n")
    finally:
        if reply_fd >= 0:
            os.close(reply_fd)


if __name__ == "__main__":
    main()
