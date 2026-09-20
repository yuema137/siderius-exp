"""Run a certified native model inside an already-confined validation worker.

Operator configuration selects the certified artifact and approved source. The
launcher must establish isolation before starting Python. This entry point does
not authenticate research requests or issue per-epoch training provenance.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Annotated

import torch
from agent.schemas.data_analysis.trained_model import TrainedModelArtifactRef
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StrictInt


class NativeModelWorkerConfig(BaseModel):
    """Protected launcher inputs; never accept these as research-side authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    root: Path
    reference: TrainedModelArtifactRef
    approved_plugin: Path
    device: str = Field(pattern=r"^(cpu|cuda:[0-9]+)$")
    deadline_epoch: FiniteFloat
    max_frame_bytes: Annotated[StrictInt, Field(ge=1024)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    with args.config.open("rb") as stream:
        payload = stream.read(65537)
    if len(payload) > 65536:
        raise ValueError("model worker configuration exceeds metadata limit")
    config = NativeModelWorkerConfig.model_validate_json(payload)
    deadline = time.monotonic() + max(0.0, config.deadline_epoch - time.time())
    if time.monotonic() >= deadline:
        return 1
    reply_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    try:
        # Native registry initialization may print diagnostics. Import it only
        # after reserving stdout exclusively for framed protocol replies.
        from experiments.shared.native_model_restore import restore_native_model
        from experiments.shared.validation_module_worker import serve_module

        with restore_native_model(
            root=config.root,
            reference=config.reference,
            approved_plugin=config.approved_plugin,
        ) as restored:
            device = torch.device(config.device)
            restored.model.to(device)
            return serve_module(
                restored.model,
                role="model",
                device=device,
                input_fd=sys.stdin.fileno(),
                output_fd=reply_fd,
                deadline=deadline,
                max_frame_bytes=config.max_frame_bytes,
            )
    finally:
        os.close(reply_fd)


if __name__ == "__main__":
    raise SystemExit(main())
