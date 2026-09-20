"""Capture actual native defaults, loader dtype semantics and clean CLI output."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

from experiments.shared.native_objective_metadata import (
    NativeObjectiveMetadata,
    ObjectiveMetadataRequest,
)


def test_actual_metadata_worker_resolves_defaults_without_constructing_loss():
    source = """from pydantic import BaseModel, Field
print("candidate import chatter")
class Config(BaseModel):
    denominator: float = 2.0
    weights: list[float] = Field(default_factory=lambda: [0.2, 0.8])
class Loss:
    def __init__(self,config):
        raise AssertionError("metadata must not construct the training loss")
PLUGIN_LOSS_TYPE="metadata_fixture"
PLUGIN_LOSS_CONFIG_CLASS=Config
PLUGIN_LOSS_CLASS=Loss
PLUGIN_LOSS_TARGET_DTYPE="float"
PLUGIN_LOSS_REDUCTION="mean"
"""
    request = ObjectiveMetadataRequest(source=source, loss_name="metadata_fixture")
    process = subprocess.run(
        [sys.executable, "-B", "-m", "experiments.shared.native_objective_metadata"],
        input=request.model_dump_json(),
        capture_output=True,
        check=False,
        text=True,
        cwd=Path(__file__).resolve().parents[2],
        env={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
        timeout=10,
    )
    assert process.returncode == 0, process.stderr
    metadata = NativeObjectiveMetadata.model_validate_json(process.stdout)
    assert metadata.effective_parameters == {"denominator": 2.0, "weights": [0.2, 0.8]}
    assert metadata.target_dtype == "float" and metadata.reduction == "mean"
    assert metadata.loss_name == "metadata_fixture"
    assert metadata.source_sha256 == hashlib.sha256(source.encode()).hexdigest()
    assert "candidate import chatter" in process.stderr
