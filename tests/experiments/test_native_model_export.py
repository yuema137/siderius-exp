"""Actual native checkpoint reconstruction reaches the unchanged candidate loader."""

import json
from pathlib import Path

import pytest
import torch
import yaml
from agent.schemas.model_io_contract import ModelIOContract
from core.sandbox_layout import training_checkpoint_path

from deployments.tidmad_coding_agent_baseline.tools.segment_inference import (
    load_candidate_model,
)
from experiments.tidmad.main_orchestrator.native_export import NativeTidmadExporter
from tests.experiments.test_baseline_evaluation_client import _client


@pytest.fixture
def trained(tmp_path, monkeypatch):
    monkeypatch.setenv("SIDERIUS_PLUGIN_DIRS", str(tmp_path))
    from ml_models.models_format_sandbox import get_config_class
    from ml_models.models_sandbox import construct_registered_model

    before_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        client, template = _client(tmp_path, "valid")
        config = get_config_class("fcnet")(segmentation_size=40000, latent_dims=[2])
        model = construct_registered_model("fcnet", config, loss_type="smooth_l1").cpu()
        optimizer = torch.optim.SGD(model.parameters(), lr=0.001)
        inputs = (torch.arange(40000).reshape(1, 40000) % 256).float()
        before = {key: value.clone() for key, value in model.state_dict().items()}
        for _ in range(2):
            optimizer.zero_grad()
            torch.nn.functional.smooth_l1_loss(model(inputs), inputs).backward()
            optimizer.step()
        assert any(
            not torch.equal(before[key], value)
            for key, value in model.state_dict().items()
        )
        models = tmp_path / "models"
        models.mkdir()
        checkpoint = training_checkpoint_path(models, "fcnet", "attempt")
        torch.save(model.state_dict(), checkpoint)
        task = (
            Path(__file__).resolve().parents[2]
            / "tasks/tidmad/declared/task_config_regression.yaml"
        )
        model_io = ModelIOContract.model_validate(
            yaml.safe_load(task.read_text())["forward_contract"]["model_io"]
        )
        request = template.model_copy(
            update={
                "model_type": "fcnet",
                "model_io": model_io,
                "models_dir": str(models),
                "model_configuration": config.model_dump(mode="json"),
                "loss_configuration": {"loss_type": "smooth_l1"},
                "training_configuration": {
                    "epochs": 2,
                    "optimizer_type": "sgd",
                    "lr": 0.001,
                },
            }
        )
        yield client, request, model.eval()
    finally:
        torch.set_num_threads(before_threads)


def test_trained_native_model_exports_and_invokes_existing_client(trained):
    client, request, model = trained
    client.exporter = NativeTidmadExporter(method="trace", inference_batch_size=2)
    result = client.evaluate(request)
    assert result.eligible_for_selection
    (candidate,) = client.settings.candidate_root.iterdir()
    restored, _ = load_candidate_model(candidate, torch.device("cpu"))
    held_out = torch.full((3, 40000), 127, dtype=torch.int64)
    torch.testing.assert_close(restored(held_out), model(held_out))
    exported_state = torch.load(candidate / "weights.pth", weights_only=True)
    for key, value in model.state_dict().items():
        assert torch.equal(exported_state["model." + key], value)
    metadata = json.loads((candidate / "native_reconstruction.json").read_text())
    assert metadata["loss_configuration"]["loss_type"] == "smooth_l1"
    assert metadata["input_dtype"] == "torch.float32"
    assert metadata["model_configuration"]["latent_dims"] == [2]
    assert metadata["training_configuration"]["epochs"] == 2
    assert (candidate / "model/model.py").is_file()
    assert (candidate / "model/config.py").is_file()
    assert result.requested_scope != result.evaluated_scope


@pytest.mark.parametrize("fault", ["missing_loss", "wrong_head", "wrong_attempt"])
def test_wrong_reconstruction_never_publishes_candidate(trained, tmp_path, fault):
    _, request, _ = trained
    updates = {
        "missing_loss": {"loss_configuration": None},
        "wrong_head": {"loss_configuration": {"loss_type": "ce"}},
        "wrong_attempt": {"exp_id": "other"},
    }
    wrong = request.model_copy(update=updates[fault])
    destination = tmp_path / "rejected"
    with pytest.raises((ValueError, RuntimeError, FileNotFoundError)):
        NativeTidmadExporter(method="trace", inference_batch_size=2)(wrong, destination)
    assert not destination.exists()
