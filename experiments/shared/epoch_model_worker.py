"""Restore a launch-bound model and epoch snapshot in a confined worker.

The launcher freezes this specification from admitted training inputs. Hashes
bind bytes, not caller authority. Run only after filesystem/network confinement;
this worker must never have target-data mounts or private service credentials.
"""

import hashlib
import inspect
import os
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Annotated, Self

import torch
from agent.schemas.data_analysis.common import Sha256
from core.local_code import (
    CodePackageDeclaration,
    MemberIdentity,
    bind_code_package,
    capture_package,
)
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

from experiments.shared.validation_snapshot import load_worker_snapshot


class StagedModelPackage(BaseModel):
    """Operator-staged finite package and the model member used in training."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    root: Path
    identity: MemberIdentity


class EpochModelSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model_type: str = Field(min_length=1)
    constructor_sha256: Sha256
    source_sha256: Sha256
    plugin_source: str | None = None
    plugin_package: StagedModelPackage | None = None

    @model_validator(mode="after")
    def one_plugin_source(self) -> Self:
        if self.plugin_source is not None and self.plugin_package is not None:
            raise ValueError("epoch model must select one plugin source representation")
        return self


class EpochModelSpecification(EpochModelSource):
    configuration: dict[str, JsonValue]
    loss_type: str = Field(min_length=1)


class EpochModelWorkerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    specification: EpochModelSpecification
    state_fd: Annotated[StrictInt, Field(ge=0)]
    max_snapshot_bytes: Annotated[StrictInt, Field(gt=0)]
    training: StrictBool
    device: str = Field(pattern=r"^(cpu|cuda:[0-9]+)$")
    deadline_epoch: FiniteFloat
    max_frame_bytes: Annotated[StrictInt, Field(ge=1024)]


@contextmanager
def bind_epoch_model_source(spec: EpochModelSource) -> Iterator[None]:
    """Bind verified source for metadata or execution inside a confined process."""
    from ml_models import models_sandbox
    from ml_models.plugin_loader import register_model_in_memory

    if (
        spec.constructor_sha256
        != models_sandbox.registered_model_construction_implementation_sha256()
    ):
        raise ValueError("epoch model constructor differs from admitted training")
    with ExitStack() as stack:
        if spec.plugin_package is not None:
            selected = spec.plugin_package
            package = capture_package(
                CodePackageDeclaration(
                    root=".",
                    files=tuple(
                        pin.member for pin in selected.identity.package.members
                    ),
                ),
                selected.root,
            )
            if package.identity != selected.identity.package:
                raise ValueError("epoch model package differs from admitted source")
            source = package.root / selected.identity.member
            member = package.member(source)
            if member is None or member.pin.content_sha256 != spec.source_sha256:
                raise ValueError("epoch model member differs from admitted source")
            stack.enter_context(bind_code_package(package))
            if register_model_in_memory(str(source)) != spec.model_type:
                raise ValueError("epoch model package registered a different identity")
        elif spec.plugin_source is not None:
            payload = spec.plugin_source.encode()
            if hashlib.sha256(payload).hexdigest() != spec.source_sha256:
                raise ValueError("epoch model source differs from admitted source")
            directory = stack.enter_context(
                tempfile.TemporaryDirectory(prefix="epoch-model-")
            )
            source = Path(directory) / "model.py"
            source.write_bytes(payload)
            if register_model_in_memory(str(source)) != spec.model_type:
                raise ValueError("epoch model plugin registered a different identity")
        else:
            model_class = models_sandbox.MODEL_REGISTRY.get(spec.model_type)
            if model_class is None or model_class.__module__ != models_sandbox.__name__:
                raise ValueError(
                    "non-builtin model requires its admitted plugin source"
                )
            source = Path(inspect.getfile(model_class))
            if hashlib.sha256(source.read_bytes()).hexdigest() != spec.source_sha256:
                raise ValueError("builtin model source differs from admitted runtime")
        yield


@contextmanager
def restore_epoch_model(config: EpochModelWorkerConfig) -> Iterator[torch.nn.Module]:
    """Use native registry construction and strict numeric state restoration."""
    from ml_models import models_sandbox
    from ml_models.models_format_sandbox import get_config_class

    spec = config.specification
    with bind_epoch_model_source(spec):
        config_class = get_config_class(spec.model_type)
        if config_class is None:
            raise ValueError("model configuration schema is unavailable")
        validated = config_class.model_validate(spec.configuration)
        model = models_sandbox.construct_registered_model(
            spec.model_type,
            validated,
            loss_type=spec.loss_type,
        ).to(torch.device(config.device))
        state = load_worker_snapshot(
            config.state_fd, max_bytes=config.max_snapshot_bytes
        )
        model.load_state_dict(state, strict=True)
        del state
        model.train(config.training)
        yield model


def main() -> int:
    from experiments.shared.validation_worker_config import read_worker_config

    config = EpochModelWorkerConfig.model_validate_json(
        read_worker_config(description=__doc__)
    )
    deadline = time.monotonic() + max(0.0, config.deadline_epoch - time.time())
    if time.monotonic() >= deadline:
        return 1
    reply_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    try:
        from experiments.shared.validation_module_worker import serve_module

        with restore_epoch_model(config) as model:
            os.close(config.state_fd)
            return serve_module(
                model,
                role="model",
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
