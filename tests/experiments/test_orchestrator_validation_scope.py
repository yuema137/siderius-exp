"""Task scope is checked before data access, without changing frozen task code."""

import json
from pathlib import Path

import h5py
import pytest
from execute_tools.dataset_config import DataScope, DatasetProfile

from experiments.tidmad.main_orchestrator.validation_scope import admit_validation_scope
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope, TidmadTaskDataPath


def _profile():
    root = Path(__file__).resolve().parents[2]
    payload = json.loads(
        (root / "tasks/tidmad/resolved/dataset_profile.json").read_text()
    )
    payload["dataset"].update(num_files=3, psd_segment_length=2000, segments_per_file=3)
    payload["anchor_selection_files"] = [0]
    payload["health_peek_files"] = [0]
    return DatasetProfile.model_validate(payload)


@pytest.mark.parametrize("embedded_profile", [False, True])
def test_admission_retains_scope_and_counts_rows_without_reading_data(
    monkeypatch, embedded_profile
):
    monkeypatch.setattr(
        h5py, "File", lambda *a, **k: pytest.fail("admission opened data")
    )
    profile = _profile()
    scope = TidmadScope(
        sample_set={1: [0, 2]},
        seg_size=1000,
        profile=profile if embedded_profile else None,
    )
    payload = TidmadTaskDataPath().serialize_scope(scope)
    admitted = admit_validation_scope(
        payload,
        profile=profile,
        allowed_scope=DataScope(file_indices=[0, 1]),
        model_segmentation_size=1000,
    )
    assert admitted.payload == payload
    assert admitted.rows == 4


@pytest.mark.parametrize("fault", ["band", "segment", "model_geometry", "profile"])
def test_mismatched_scope_refuses_before_materialization(fault, monkeypatch):
    monkeypatch.setattr(
        h5py, "File", lambda *a, **k: pytest.fail("refusal opened data")
    )
    profile = _profile()
    data = {2: [0]} if fault == "band" else {1: [3] if fault == "segment" else [0]}
    selected = profile
    if fault == "profile":
        values = profile.to_wire()
        values["dataset"]["segments_per_file"] = 4
        selected = DatasetProfile.model_validate(values)
    scope = TidmadScope(
        sample_set=data,
        seg_size=500 if fault == "model_geometry" else 1000,
        profile=selected,
    )
    with pytest.raises(ValueError):
        admit_validation_scope(
            TidmadTaskDataPath().serialize_scope(scope),
            profile=profile,
            allowed_scope=DataScope(file_indices=[0, 1]),
            model_segmentation_size=1000,
        )


@pytest.mark.parametrize(
    "fault",
    [None, "manifest_path", "manifest_bytes", "adapter", "profile", "scope_digest"],
)
def test_captured_invocation_binds_operator_task_before_data_access(
    tmp_path, monkeypatch, fault
):
    import hashlib
    import os

    from execute_tools.scope_artifact import ScopeArtifactError, write_scope_artifact

    from experiments.shared.native_training_inputs import capture_native_training_inputs
    from experiments.tidmad.main_orchestrator.validation_scope import (
        admit_captured_validation_scope,
    )

    monkeypatch.setattr(
        h5py, "File", lambda *a, **k: pytest.fail("task admission opened data")
    )
    profile = _profile()
    source_profile = profile.to_wire()
    if fault == "profile":
        source_profile["dataset"]["segments_per_file"] = 4
    for name, value in (
        ("model", {}),
        ("train", {}),
        ("loss", {}),
        ("profile", source_profile),
    ):
        (tmp_path / f"{name}.json").write_text(json.dumps(value))
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"frozen":"synthetic"}')
    manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    other = tmp_path / "other.json"
    other.write_bytes(manifest.read_bytes())
    payload = TidmadTaskDataPath().serialize_scope(
        TidmadScope(sample_set={1: [0, 2]}, seg_size=1000, profile=profile)
    )
    digest = write_scope_artifact(str(tmp_path / "scope.json"), payload)
    command = [
        "python",
        "native.py",
        "--model_cfg",
        "model.json",
        "--train_cfg",
        "train.json",
        "--loss_cfg",
        "loss.json",
        "--dataset_profile_json",
        "profile.json",
        "--task_manifest",
        "other.json" if fault == "manifest_path" else "manifest.json",
        "--task_data_path_id",
        "other" if fault == "adapter" else "tidmad",
        "--task_eval_scope_ref",
        "scope.json",
        "--task_eval_scope_digest",
        "0" * 64 if fault == "scope_digest" else digest,
    ]
    parent = tmp_path / "operator"
    parent.mkdir(mode=0o700)
    captured = capture_native_training_inputs(
        command,
        python=Path("python"),
        entrypoint=Path("native.py"),
        source_cwd=tmp_path,
        allowed_roots=(tmp_path,),
        parent=parent,
        owner_uid=os.geteuid(),
        max_file_bytes=100000,
    )
    if fault == "manifest_bytes":
        manifest.write_text('{"frozen":"changed"}')
    kwargs = {
        "manifest": manifest,
        "manifest_sha256": manifest_hash,
        "task_data_path_id": "tidmad",
        "source_cwd": tmp_path,
        "profile": profile,
        "allowed_scope": DataScope(file_indices=[0, 1]),
        "model_segmentation_size": 1000,
    }
    if fault:
        expected = ScopeArtifactError if fault == "scope_digest" else ValueError
        with pytest.raises(expected):
            admit_captured_validation_scope(captured, **kwargs)
    else:
        admitted = admit_captured_validation_scope(captured, **kwargs)
        assert admitted.payload == payload and admitted.rows == 4
