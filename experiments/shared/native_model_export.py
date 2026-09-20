"""Reconstruct a native checkpoint using the framework's existing registries.

Research-side execution only: model constructors and forwards are generated code.
The caller must bind the same model registry/task contract as the training call.
"""

import inspect
import json
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import torch
from core.sandbox_layout import training_checkpoint_path
from execute_tools.evaluation_execution import CandidateEvaluationRequest
from execute_tools.model_input_dtype import (
    apply_contract_cardinality,
    resolve_inference_input_dtype,
)
from ml_models.models_format_sandbox import LossConfig, get_config_class
from ml_models.models_sandbox import construct_registered_model

from experiments.shared.checksum_manifest import sha256_file
from experiments.shared.scripted_model_export import (
    ScriptedExportReceipt,
    export_scripted_model,
)


class NativeInputAdapter(torch.nn.Module):
    """Apply the native inference dtype conversion before the registered model."""

    def __init__(self, model: torch.nn.Module, input_dtype: torch.dtype | None):
        super().__init__()
        self.model = model
        self.input_dtype = input_dtype

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        if self.input_dtype is None:
            return self.model(value)
        return self.model(value.to(dtype=self.input_dtype))


def export_native_model(
    request: CandidateEvaluationRequest,
    destination: Path,
    *,
    examples: Sequence[tuple[torch.Tensor, ...]],
    method: Literal["script", "trace"],
) -> ScriptedExportReceipt:
    """Restore exact checkpoint state, then export and retain reconstruction facts.

    Metadata records the observed checkpoint/source hashes and bound public
    configuration. This is not privileged training certification. The serialized
    model is self-contained; source files are retained for diagnosis.
    """
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    if request.loss_configuration is None:
        raise ValueError("native export requires explicit effective loss configuration")
    loss = LossConfig.model_validate(request.loss_configuration)
    config_type = get_config_class(request.model_type)
    if config_type is None:
        raise ValueError("native export model configuration is not registered")
    configuration = config_type(
        **apply_contract_cardinality(request.model_configuration, request.model_io)
    )
    checkpoint = training_checkpoint_path(
        request.models_dir, request.model_type, request.exp_id
    )
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model = construct_registered_model(
        request.model_type, configuration, loss_type=loss.loss_type
    ).cpu()
    model.load_state_dict(state, strict=True)
    model.eval()
    input_dtype = resolve_inference_input_dtype(request.model_type, request.model_io)
    adapted = NativeInputAdapter(model, input_dtype).eval()
    sources = {}
    for role, implementation in (("model", type(model)), ("config", config_type)):
        source = inspect.getsourcefile(implementation)
        if source is None:
            raise ValueError(
                f"native export cannot retain {role} implementation source"
            )
        path = Path(source)
        sources[role] = (path, path.read_bytes())
    receipt = export_scripted_model(
        adapted, examples=examples, destination=destination, method=method
    )
    try:
        source_dir = destination / "model"
        source_dir.mkdir()
        for role, (_, payload) in sources.items():
            (source_dir / f"{role}.py").write_bytes(payload)
        shutil.copyfile(Path(__file__), source_dir / "input_adapter.py")
        metadata = {
            "run_name": request.run_name,
            "exp_id": request.exp_id,
            "model_type": request.model_type,
            "checkpoint_path": str(checkpoint),
            "checkpoint_sha256": sha256_file(checkpoint),
            "model_configuration": configuration.model_dump(mode="json"),
            "training_configuration": request.training_configuration,
            "loss_configuration": loss.model_dump(mode="json"),
            "model_io": request.model_io.model_dump(mode="json")
            if request.model_io
            else None,
            "input_dtype": str(input_dtype) if input_dtype else None,
            "model_class": f"{type(model).__module__}:{type(model).__qualname__}",
            "config_class": f"{config_type.__module__}:{config_type.__qualname__}",
            "source_sha256": {
                role: sha256_file(source_dir / f"{role}.py") for role in sources
            },
        }
        (destination / "native_reconstruction.json").write_text(
            json.dumps(metadata, indent=2) + "\n"
        )
        (destination / "train_config.json").write_text(
            json.dumps(request.training_configuration, indent=2) + "\n"
        )
        return receipt
    except BaseException:
        shutil.rmtree(destination)
        raise
