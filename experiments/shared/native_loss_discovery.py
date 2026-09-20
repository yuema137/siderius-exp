"""Observe native custom-loss selection in a confined, target-free fresh process."""

import hashlib
import os
import sys
from contextlib import nullcontext
from pathlib import Path

from agent.schemas.data_analysis.common import Sha256
from core.local_code import CodePackageDeclaration, bind_code_package, capture_package
from pydantic import BaseModel, ConfigDict, Field


class LossDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    loss_name: str = Field(min_length=1)
    code_package: CodePackageDeclaration | None = None


class NativeLossSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    loss_name: str
    plugin_path: Path
    source_sha256: Sha256


def discover_loss(request: LossDiscoveryRequest) -> NativeLossSelection:
    """Use installed native directory precedence; do not construct the criterion."""
    from ml_models.loss_plugin_loader import load_loss_plugin

    binding = (
        bind_code_package(capture_package(request.code_package, Path.cwd()))
        if request.code_package is not None
        else nullcontext()
    )
    with binding:
        plugin = load_loss_plugin(request.loss_name)
    if plugin is None:
        raise ValueError("requested loss is absent from native plugin selection")
    source = Path(plugin["plugin_path"])
    with source.open("rb") as stream:
        payload = stream.read(1048577)
    if len(payload) > 1048576:
        raise ValueError("native loss declaration exceeds source limit")
    return NativeLossSelection(
        loss_name=plugin["loss_type"],
        plugin_path=source,
        source_sha256=hashlib.sha256(payload).hexdigest(),
    )


def main() -> None:
    payload = sys.stdin.buffer.read(65537)
    if len(payload) > 65536:
        raise ValueError("loss discovery request exceeds limit")
    request = LossDiscoveryRequest.model_validate_json(payload)
    reply_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    try:
        result = discover_loss(request)
        with os.fdopen(reply_fd, "w") as reply:
            reply_fd = -1
            reply.write(result.model_dump_json() + "\n")
    finally:
        if reply_fd >= 0:
            os.close(reply_fd)


if __name__ == "__main__":
    main()
