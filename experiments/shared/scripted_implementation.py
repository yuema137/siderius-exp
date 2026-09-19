"""Research-side native implementation with a required serialization gate.

Invoke in the caller's isolated research worker. This does not authorize code,
create a sandbox, train, or replace the native code validator.
"""

import hashlib
import json
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

import torch
from agent.schemas.implementor import ImplementorInput, ImplementorOutput
from ml_models.models_format_sandbox import get_config_class
from ml_models.models_sandbox import construct_registered_model
from ml_models.plugin_loader import register_model_in_memory
from pydantic import BaseModel, ConfigDict

from experiments.shared.scripted_model_export import qualify_scripted_model

_DELIVERY_REQUIREMENT = (
    "Deployment deliverable: the evaluation-mode model must support torch.jit.script "
    "and preserve native outputs and state_dict on the declared input contract. "
    "Do not use tracing as a substitute. This is a submission-format requirement; "
    "preserve the proposed architecture and scientific settings."
)


class NativeImplementor(Protocol):
    def run(self, inp: ImplementorInput) -> ImplementorOutput: ...


class QualifiedImplementation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    implementation: ImplementorOutput
    qualified_model_config: dict[str, Any]
    source_sha256: str
    example_count: int
    loss_type: str


class ImplementationExportError(ValueError):
    """Use this bounded diagnostic as previous_validation_failure on a retry."""


def implement_for_scripted_export(
    implementor: NativeImplementor,
    request: ImplementorInput,
    *,
    examples: Sequence[tuple[torch.Tensor, ...]],
) -> QualifiedImplementation:
    """Run the native implementor, then gate its concrete initial configuration.

    Delivery requirements travel through task_description, never human_advice.
    The result qualifies only these source/config/loss bytes and examples. Any
    tuner configuration change needs another qualification; trained weights must
    still pass the final exporter. Caller owns retries and all resource limits.
    """
    if not examples or any(
        not args or any(value.device.type != "cpu" for value in args)
        for args in examples
    ):
        raise ValueError("implementation qualification requires explicit CPU examples")
    # Fail before a provider call if the caller has not supplied construction inputs.
    config = dict(request.baseline_config["model_config"])
    loss_type = request.baseline_config["loss_config"]["loss_type"]
    if not isinstance(loss_type, str) or not loss_type:
        raise ValueError("implementation qualification requires an explicit loss_type")
    values = request.model_dump()
    values["task_description"] = (
        request.task_description + "\n\n" + _DELIVERY_REQUIREMENT
    )
    bound = ImplementorInput.model_validate(values)
    output = ImplementorOutput.model_validate(implementor.run(bound))
    if (
        output.model_type != request.model_name
        or output.candidate_id != request.candidate_id
    ):
        raise ValueError("native implementation changed candidate/model identity")
    for field, adjustment in output.baseline_config_adjustments.items():
        if field not in config or config[field] != adjustment.original_value:
            raise ValueError("implementation adjustment does not match proposed config")
        config[field] = adjustment.adjusted_value
    source = Path(output.model_file_path).read_bytes()
    # Keep an immutable byte snapshot and its source file alive through scripting.
    with tempfile.TemporaryDirectory(
        prefix="implementation-export-check-"
    ) as directory:
        plugin = Path(directory) / "model.py"
        plugin.write_bytes(source)
        try:
            if register_model_in_memory(str(plugin)) != output.model_type:
                raise ValueError("plugin registered a different model type")
            schema = get_config_class(output.model_type)
            if schema is None:
                raise ValueError("plugin did not register a config schema")
            validated = schema.model_validate(config)
            model = construct_registered_model(
                output.model_type, validated, loss_type=loss_type
            )
            qualify_scripted_model(model.cpu().eval(), examples)
        except Exception as error:
            detail = str(error.__cause__ or error)[-3000:]
            raise ImplementationExportError(
                "Pre-training export qualification failed; repair the implementation "
                "without changing the scientific contract. " + detail
            ) from error
    # Keep exactly the selected config, without silently replacing it with defaults.
    return QualifiedImplementation(
        implementation=output,
        qualified_model_config=json.loads(json.dumps(config)),
        source_sha256=hashlib.sha256(source).hexdigest(),
        example_count=len(examples),
        loss_type=loss_type,
    )
