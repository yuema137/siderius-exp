"""Restore certified native weights inside a caller-owned research worker."""

import hashlib
import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import torch
from agent.schemas.data_analysis.trained_model import (
    TrainedModelArtifact,
    TrainedModelArtifactRef,
)
from execute_tools.trained_model_artifact import (
    copy_certified_artifact,
    read_certified_artifact,
)
from ml_models.models_format_sandbox import get_config_class
from ml_models.models_sandbox import (
    construct_registered_model,
    registered_model_construction_implementation_sha256,
)
from ml_models.plugin_loader import register_model_in_memory


@dataclass(frozen=True)
class RestoredNativeModel:
    """Ephemeral model and its certified inputs; source exists during the context."""

    model: torch.nn.Module
    artifact: TrainedModelArtifact
    source: bytes
    config: bytes
    descriptor: bytes


@contextmanager
def restore_native_model(
    *, root: Path, reference: TrainedModelArtifactRef, approved_plugin: Path
) -> Iterator[RestoredNativeModel]:
    """Verify all input bytes before importing an explicitly approved plugin.

    The caller must run this in a fresh resource-limited research process with
    no private data access. This is not an authorization service or sandbox.
    Keep the context open through scripting: TorchScript needs the source file.
    """
    descriptor = read_certified_artifact(root, reference.artifact_ref)
    artifact = TrainedModelArtifact.model_validate_json(descriptor)
    if (
        artifact.model_artifact_id != reference.model_artifact_id
        or artifact.executable_model_identity_sha256
        != reference.executable_model_identity_sha256
    ):
        raise ValueError(
            "native model reference does not identify the certified artifact"
        )
    construction = artifact.model_construction_contract
    if (
        construction.implementation_sha256
        != registered_model_construction_implementation_sha256()
    ):
        raise ValueError(
            "native model construction implementation differs from training"
        )
    identity = artifact.model_plugin_identity
    if identity.local_code_identity_sha256 is not None:
        raise ValueError("packaged native plugins need their bound package executor")
    inference = artifact.model_io_contract.inference
    if (
        inference is None
        or inference.prediction_decoder_protocol_id
        != "siderius.identity-prediction-decoder.v1"
        or any(
            x.information_class == "metadata" for x in inference.required_information
        )
    ):
        raise ValueError(
            "native export requires identity decoding without metadata adapters"
        )
    source = approved_plugin.read_bytes()
    if hashlib.sha256(source).hexdigest() != identity.content_sha256:
        raise ValueError("approved native plugin differs from certified source")
    config = read_certified_artifact(root, artifact.model_config_ref)
    with tempfile.TemporaryDirectory(prefix="native-model-restore-") as temporary:
        scratch = Path(temporary)
        plugin = scratch / "model.py"
        plugin.write_bytes(source)
        checkpoint = scratch / "weights.pth"
        copy_certified_artifact(root, artifact.checkpoint.ref, checkpoint)
        # Import only after every external byte used below was checked and copied.
        registered = register_model_in_memory(str(plugin))
        if registered != identity.model_type:
            raise ValueError("certified plugin registered a different model type")
        config_class = get_config_class(identity.model_type)
        if config_class is None:
            raise ValueError("certified plugin did not register its config schema")
        validated = config_class.model_validate(json.loads(config))
        model = construct_registered_model(
            identity.model_type, validated, loss_type=construction.loss_type
        )
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        model.load_state_dict(state, strict=True)
        model.cpu().eval()
        yield RestoredNativeModel(model, artifact, source, config, descriptor)
