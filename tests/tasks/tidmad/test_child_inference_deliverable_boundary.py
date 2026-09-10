"""A real CPU inference child persists the explicitly transported task scope.

This replaces the retired implicit-default Step-05c subprocess witness.
The checkpoint is deterministic test input, not evidence of model training.
No subprocess/model/writer is mocked and no source path is injected.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import h5py
import numpy as np
import torch
from execute_tools.scope_artifact import write_scope_artifact
from execute_tools.task_data_path import content_identity
from ml_models.models_format_sandbox import get_config_class
from ml_models.models_sandbox import MODEL_REGISTRY
from workflows.task_composition import compose_task_data_path_from_manifest

from tests.helpers.d14_tidmad_fixture import write_two_family_fixture

EXP_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = EXP_ROOT / "tasks/tidmad/compositions/bounded_qualification.yaml"


def test_real_inference_child_writes_exact_scoped_artifact(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    fixture = write_two_family_fixture(
        data, num_files=1, psd_segment_length=2000, segments_per_file=2, seg_size=1000
    )
    # Every decoded int8 edge is checked, and segment 0 differs from segment 1.
    target = np.tile(np.array([-128, -1, 0, 1, 127, 63, -64, 100], dtype=np.int8), 500)
    target[:2000] = 42
    with h5py.File(fixture.validation_path(0), "r+") as handle:
        handle["timeseries/channel0002/timeseries"][:] = target

    adapter = compose_task_data_path_from_manifest(str(MANIFEST))
    scope_type = sys.modules[type(adapter).__module__].TidmadScope
    scope = scope_type(sample_set={0: [1]}, seg_size=1000, profile=fixture.profile)
    scope_path = tmp_path / "eval_scope.json"
    digest = write_scope_artifact(str(scope_path), adapter.serialize_scope(scope))
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(fixture.profile.model_dump_json())

    model_config = {
        "model_type": "wavenet",
        "segmentation_size": 1000,
        "input_channels": 4,
        "residual_channels": 8,
        "gate_channels": 8,
        "skip_channels": 8,
        "kernel_size": 2,
        "num_blocks": 1,
    }
    model = MODEL_REGISTRY["wavenet"](get_config_class("wavenet")(**model_config))
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    checkpoint = tmp_path / "model.pth"
    torch.save(model.state_dict(), checkpoint)
    (tmp_path / "_OK_child_boundary").touch()
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model_config))
    loss_path = tmp_path / "loss.json"
    loss_path.write_text(json.dumps({"loss_type": "ce"}))
    output = tmp_path / "output"
    output.mkdir()

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.update(
        CUDA_VISIBLE_DEVICES="",
        PYTHONDONTWRITEBYTECODE="1",
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    child = subprocess.run(
        [
            sys.executable,
            "-m",
            "execute_tools.inference_single",
            "--mode",
            "agent",
            "-m",
            "wavenet",
            "--task_manifest",
            str(MANIFEST),
            "--task_data_path_id",
            adapter.task_data_path_id,
            "--task_data_path_identity",
            content_identity(adapter),
            "--task_eval_scope_ref",
            str(scope_path),
            "--task_eval_scope_digest",
            digest,
            "--dataset_profile_json",
            str(profile_path),
            "--model_cfg",
            str(model_path),
            "--loss_cfg",
            str(loss_path),
            "--model_path",
            str(checkpoint),
            "--exp_id",
            "child_boundary",
            "--run_name",
            "explicit_scope",
            "--data_dir",
            str(data),
            "--output_dir",
            str(output),
            "--inference_batch_size",
            "1",
            "--file_index",
            "0",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
    )
    assert child.returncode == 0, child.stdout + child.stderr
    assert "[generic_inference] 2 sample(s) in 2 batch(es)" in child.stdout

    expected = (
        output
        / "abra_validation_denoised_wavenet_explicit_scope_child_boundary_0000.h5"
    )
    assert list(output.glob("*.h5")) == [expected]
    with h5py.File(expected, "r") as handle:
        assert sorted(handle["timeseries"]) == ["channel0001", "channel0002"]
        prediction = handle["timeseries/channel0001/timeseries"]
        truth = handle["timeseries/channel0002/timeseries"]
        assert prediction.shape == truth.shape == (2000,)
        assert prediction.dtype == truth.dtype == np.dtype("int8")
        # Zero logits select class zero; persisted ADC decoding subtracts 128.
        np.testing.assert_array_equal(prediction[:], np.full(2000, -128, dtype=np.int8))
        np.testing.assert_array_equal(truth[:], target[2000:])
    assert len(list(data.glob("*.h5"))) == 2
