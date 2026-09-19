"""Restoration verifies certification before code execution and uses native construction."""

import hashlib
import json

import pytest
import torch
from agent.schemas.data_analysis.common import CertifiedArtifactRef
from agent.schemas.data_analysis.trained_model import (
    CheckpointArtifact,
    ModelConstructionContract,
    ModelEnvironmentIdentity,
    ModelPluginIdentity,
    TaskInferenceBindingIdentity,
    TrainedModelArtifact,
    TrainedModelArtifactRef,
)
from agent.schemas.model_io_contract import ModelIOContract
from agent.schemas.task_config import ForwardContract
from ml_models.models_sandbox import registered_model_construction_implementation_sha256

from experiments.shared import native_model_restore as restore


def _ref(path):
    data = path.read_bytes()
    return CertifiedArtifactRef(
        logical_ref=path.name,
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        media_type="application/octet-stream",
    )


@pytest.fixture
def certified(tmp_path):
    plugin = tmp_path / "source.py"
    plugin.write_text("""import torch
from pydantic import BaseModel
class Config(BaseModel):
    model_type: str = "export_synthetic"
class Model(torch.nn.Module):
    def __init__(self, config, *, loss_type):
        super().__init__()
        if loss_type != "smooth_l1":
            raise ValueError("construction lost certified loss")
        self.scale = torch.nn.Parameter(torch.tensor(0.0))
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * self.scale
PLUGIN_MODEL_TYPE = "export_synthetic"
PLUGIN_OUTPUT_TYPE = "regressor"
PLUGIN_CONFIG_CLASS = Config
PLUGIN_MODEL_CLASS = Model
""")
    weights = tmp_path / "weights.pt"
    torch.save({"scale": torch.tensor(3.0)}, weights)
    config = tmp_path / "config.json"
    config.write_text('{"model_type":"export_synthetic"}')
    tensor = {
        "axes": [
            {"role": "batch", "dimension": {"symbolic": "B"}},
            {"dimension": {"fixed": 2}},
        ],
        "dtype": {"admissible": ["float32"]},
    }
    io = ModelIOContract.model_validate(
        {
            "input": tensor,
            "output": tensor,
            "inference": {
                "accepted_input_view_formats": ["siderius.numeric-array.v1"],
                "required_information": [{"information_class": "data"}],
                "prediction_output_format": "siderius.numeric-array.v1",
                "prediction_semantic_id": "synthetic.vector.v1",
            },
        }
    )
    parts = {
        "checkpoint": CheckpointArtifact(ref=_ref(weights)),
        "model_config_ref": _ref(config),
        "model_plugin_identity": ModelPluginIdentity(
            configured_ref="approved",
            member="source.py",
            model_type="export_synthetic",
            content_sha256=_ref(plugin).sha256,
        ),
        "model_construction_contract": ModelConstructionContract(
            loss_type="smooth_l1",
            implementation_sha256=registered_model_construction_implementation_sha256(),
        ),
        "model_io_contract": io,
        "forward_contract": ForwardContract(model_io=io),
        "task_inference_binding": TaskInferenceBindingIdentity(
            task_data_path_id="synthetic",
            task_data_path_content_sha256="1" * 64,
            dataset_profile_sha256="2" * 64,
            task_composition_fingerprint="3" * 64,
        ),
        "environment_identity": ModelEnvironmentIdentity(
            python_version="3.12", siderius_revision="test"
        ),
    }
    identity = TrainedModelArtifact.compute_executable_identity_sha256(**parts)
    artifact = TrainedModelArtifact(
        **parts,
        model_artifact_id="synthetic-model",
        executable_model_identity_sha256=identity,
        training_scope={
            "split_id": "train",
            "scope_id": "synthetic",
            "scope_sha256": "4" * 64,
        },
        training_run={
            "run_name": "run",
            "iteration_id": "iteration-1",
            "experiment_id": "candidate-1",
        },
        provenance={
            "produced_at": "2026-09-19T00:00:00+00:00",
            "producer": "synthetic",
        },
    )
    descriptor = tmp_path / "artifact.json"
    descriptor.write_text(artifact.model_dump_json())
    reference = TrainedModelArtifactRef(
        artifact_ref=_ref(descriptor),
        model_artifact_id=artifact.model_artifact_id,
        executable_model_identity_sha256=identity,
    )
    return tmp_path, reference, plugin


def test_native_constructor_and_certified_weights_survive_restore(certified):
    root, reference, plugin = certified
    with restore.restore_native_model(
        root=root, reference=reference, approved_plugin=plugin
    ) as result:
        assert torch.equal(
            result.model(torch.tensor([[2.0, 6.0]])), torch.tensor([[6.0, 18.0]])
        )
        assert not result.model.training
        assert json.loads(result.config)["model_type"] == "export_synthetic"


@pytest.mark.parametrize("corrupted", ["source.py", "config.json", "weights.pt"])
def test_corruption_is_refused_before_plugin_import(certified, monkeypatch, corrupted):
    root, reference, plugin = certified
    with (root / corrupted).open("ab") as stream:
        stream.write(b"corruption")
    monkeypatch.setattr(
        restore,
        "register_model_in_memory",
        lambda _: pytest.fail("import before certification"),
    )
    with (
        pytest.raises(ValueError, match="differs|digest|byte size"),
        restore.restore_native_model(
            root=root, reference=reference, approved_plugin=plugin
        ),
    ):
        pytest.fail("corrupted model restored")
