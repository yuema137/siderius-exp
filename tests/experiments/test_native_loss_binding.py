"""Per-invocation source binding preserves successive and parallel objectives."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import torch
from ml_models import loss_models_sandbox as losses

from experiments.shared.native_loss_binding import AdmittedLossSource, bind_native_loss

SOURCE = """import torch
from pydantic import BaseModel
class Config(BaseModel):
    scale: float = SCALE
class Loss(torch.nn.Module):
    def __init__(self, config):
        super().__init__()
        self.scale = config.scale
    def forward(self, prediction, target):
        return ((prediction-target)**2).mean()*self.scale
PLUGIN_LOSS_TYPE="same_name"
PLUGIN_LOSS_CONFIG_CLASS=Config
PLUGIN_LOSS_CLASS=Loss
PLUGIN_LOSS_TARGET_DTYPE="float"
"""


def declaration(scale):
    return AdmittedLossSource(
        source=SOURCE.replace("SCALE", str(scale)),
        loss_name="same_name",
        parameters={"scale": float(scale)},
    )


def test_successive_versions_restore_registry_and_use_new_loss():
    before = dict(losses.LOSS_REGISTRY)
    for scale in (2, 3):
        with bind_native_loss(declaration(scale)):
            criterion = losses.LOSS_REGISTRY["same_name"](
                losses.LOSS_CONFIG_REGISTRY["same_name"]()
            )
            assert criterion(torch.ones(1), torch.zeros(1)).item() == scale
        assert losses.LOSS_REGISTRY == before


def test_wrong_defaults_restore_registry_without_entering_training():
    before = dict(losses.LOSS_REGISTRY)
    source = declaration(2).model_copy(update={"parameters": {"scale": 3.0}})
    with pytest.raises(ValueError, match="defaults differ"), bind_native_loss(source):
        pytest.fail("training must not start with different effective parameters")
    assert losses.LOSS_REGISTRY == before


def test_parallel_children_can_use_different_versions_with_identical_name():
    code = """import sys, torch
from experiments.shared.native_loss_binding import AdmittedLossSource, bind_native_loss
source = AdmittedLossSource.model_validate_json(sys.stdin.readline())
with bind_native_loss(source):
    from ml_models import loss_models_sandbox as losses
    criterion = losses.LOSS_REGISTRY[source.loss_name](losses.LOSS_CONFIG_REGISTRY[source.loss_name]())
    print("READY", flush=True)
    assert sys.stdin.readline().strip() == "GO"
    assert criterion(torch.ones(1), torch.zeros(1)).item() == source.parameters["scale"]
"""
    children = []
    try:
        for scale in (2, 3):
            child = subprocess.Popen(
                [sys.executable, "-c", code],
                cwd=Path(__file__).resolve().parents[2],
                env={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            children.append(child)
            child.stdin.write(declaration(scale).model_dump_json() + "\n")
            child.stdin.flush()
        # Both registries are populated before either child executes its loss.
        for child in children:
            assert child.stdout.readline().strip() == "READY"
        for child in children:
            _, stderr = child.communicate("GO\n", timeout=15)
            assert child.returncode == 0, stderr
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
