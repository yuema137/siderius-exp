"""Resolve captured native configurations in a confined, target-free process.

Candidate configuration classes can execute code. The protected launcher must
confine this CLI before use and bind its request to captured invocation inputs.
Run once before training, not per epoch. No model or optimizer is constructed.
"""

import hashlib
import json
import os
import sys

from agent.schemas.model_io_contract import ModelIOContract
from core.runtime_control.session import RuntimeControlPolicy
from execute_tools.model_input_dtype import apply_contract_cardinality
from execute_tools.training_cli import build_training_parser
from ml_models.models_format_sandbox import LossConfig, TrainConfig, get_config_class
from pydantic import BaseModel, ConfigDict, JsonValue

from experiments.shared.epoch_model_worker import (
    EpochModelSource,
    EpochModelSpecification,
    bind_epoch_model_source,
)
from experiments.shared.native_training_inputs import CapturedNativeInputs


class NativeConfigurationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: EpochModelSource
    model_parameters: dict[str, JsonValue]
    training: TrainConfig
    loss: LossConfig
    model_io: ModelIOContract | None = None


class NativeConfigurationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model: EpochModelSpecification
    training: TrainConfig
    loss: LossConfig
    model_io: ModelIOContract | None


def captured_configuration_request(
    captured: CapturedNativeInputs, *, source: EpochModelSource
) -> tuple[NativeConfigurationRequest, int]:
    """Build the metadata request and native epoch ceiling from captured bytes.

    Called by the protected launcher, with its own capture and admitted source.
    This does not import candidate code or authenticate a research-supplied
    capture receipt. Only the resulting request enters the confined metadata CLI.
    Runtime budget activation follows the native observation-output switch;
    training itself still owns time/step admission and early termination.
    """
    args = build_training_parser().parse_args(captured.command[2:])
    files = {item.argument: item for item in captured.files}

    def read(name: str):
        item = files[name]
        if getattr(args, name) != str(item.captured):
            raise ValueError("native configuration path differs from captured input")
        payload = item.captured.read_bytes()
        if hashlib.sha256(payload).hexdigest() != item.sha256:
            raise ValueError("native configuration changed after capture")
        return json.loads(payload)

    request = NativeConfigurationRequest(
        source=source,
        model_parameters=read("model_cfg"),
        training=read("train_cfg"),
        loss=read("loss_cfg"),
        model_io=read("model_io_json") if args.model_io_json else None,
    )
    epochs = request.training.epochs
    if args.runtime_observation_out and args.runtime_policy_json:
        policy = RuntimeControlPolicy.model_validate(read("runtime_policy_json"))
        if policy.training_budget is not None:
            epochs = policy.training_budget.max_epochs
    return request, epochs


def resolve_native_configuration(
    request: NativeConfigurationRequest,
) -> NativeConfigurationMetadata:
    """Reuse the native model schema and contract-cardinality interpreter."""
    if request.model_parameters.get("model_type") != request.source.model_type:
        raise ValueError("native model config differs from captured source selection")
    with bind_epoch_model_source(request.source):
        config_class = get_config_class(request.source.model_type)
        if config_class is None:
            raise ValueError("native model configuration schema is unavailable")
        configuration = config_class(
            **apply_contract_cardinality(request.model_parameters, request.model_io)
        )
        return NativeConfigurationMetadata(
            model=EpochModelSpecification(
                **request.source.model_dump(),
                configuration=configuration.model_dump(mode="json"),
                loss_type=request.loss.loss_type,
            ),
            training=request.training,
            loss=request.loss,
            model_io=request.model_io,
        )


def main() -> None:
    payload = sys.stdin.buffer.read(4194305)
    if len(payload) > 4194304:
        raise ValueError("native configuration request exceeds limit")
    request = NativeConfigurationRequest.model_validate_json(payload)
    reply_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    try:
        result = resolve_native_configuration(request)
        with os.fdopen(reply_fd, "w") as reply:
            reply_fd = -1
            reply.write(result.model_dump_json() + "\n")
    finally:
        if reply_fd >= 0:
            os.close(reply_fd)


if __name__ == "__main__":
    main()
