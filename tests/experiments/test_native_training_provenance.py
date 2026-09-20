"""Private-capture removal must not break public trained-model certification."""

import hashlib
import shutil
from pathlib import Path

import pytest
from execute_tools.trained_model_artifact import (
    TrainedModelEmissionContext,
    TrainingArtifactCandidate,
    emit_trained_model_artifact,
)
from workflows.task_composition import compose_run_task_bindings

from experiments.shared.native_training_provenance import (
    publish_training_candidate_sources,
)


def candidate_files(tmp_path):
    private = tmp_path / "private"
    private.mkdir()
    files = {}
    for name, payload in (
        ("config.json", b'{"width":2}'),
        ("model.py", b"# selected model\n"),
        ("scope.json", b'{"rows":[1,2]}'),
    ):
        path = private / name
        path.write_bytes(payload)
        files[name] = path
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint fixture: provenance only")
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    candidate = TrainingArtifactCandidate(
        checkpoint_path=str(checkpoint),
        checkpoint_sha256=digest(checkpoint),
        checkpoint_byte_size=checkpoint.stat().st_size,
        model_config_path=str(files["config.json"]),
        model_config_sha256=digest(files["config.json"]),
        model_config_byte_size=files["config.json"].stat().st_size,
        model_plugin_path=str(files["model.py"]),
        model_plugin_sha256=digest(files["model.py"]),
        model_plugin_member="model.py",
        model_type="fixture",
        effective_loss_type="smooth_l1",
        training_scope_path=str(files["scope.json"]),
        training_scope_sha256=digest(files["scope.json"]),
    )
    sidecar = tmp_path / "candidate.json"
    sidecar.write_text(candidate.model_dump_json())
    return private, sidecar, candidate


def test_original_capture_can_disappear_before_public_artifact_emission(tmp_path):
    private, sidecar, original = candidate_files(tmp_path)
    publish_training_candidate_sources(sidecar)
    publish_training_candidate_sources(sidecar)  # Retrying the same evidence is safe.
    published = TrainingArtifactCandidate.model_validate_json(sidecar.read_bytes())
    shutil.rmtree(private)
    changed = {"model_config_path", "model_plugin_path", "training_scope_path"}
    assert original.model_dump(exclude=changed) == published.model_dump(exclude=changed)
    for field in changed:
        assert Path(getattr(published, field)).is_file()
    root = Path(__file__).resolve().parents[2]
    composition = compose_run_task_bindings(
        str(root / "tasks/tidmad/compositions/continuous_regression_frozen_pool.yaml")
    )
    artifact = emit_trained_model_artifact(
        published,
        TrainedModelEmissionContext(
            workspace=str(tmp_path / "artifacts"),
            run_name="run",
            iteration_id="iteration",
            experiment_id="attempt",
            model_io_contract=composition.forward_contract.model_io,
            forward_contract=composition.forward_contract,
            dataset_profile={},
            task_data_path_id="fixture",
            task_data_path_content_sha256="a" * 64,
            task_composition_fingerprint="b" * 64,
            plugin_configured_ref="fixture-model",
        ),
    )
    assert (tmp_path / "artifacts" / artifact.artifact_ref.logical_ref).is_file()


def test_changed_capture_does_not_rewrite_candidate_identity(tmp_path):
    _, sidecar, original = candidate_files(tmp_path)
    before = sidecar.read_bytes()
    Path(original.model_config_path).write_text("changed")
    with pytest.raises(ValueError, match="changed before publication"):
        publish_training_candidate_sources(sidecar)
    assert sidecar.read_bytes() == before


def test_deployment_entry_publishes_after_native_execution(tmp_path, monkeypatch):
    # Deleting the post-training call must fail even if the standalone copier works.
    from core.sandbox_executor import sandbox_records_dir
    from execute_tools.trained_model_artifact import training_artifact_candidate_path

    from experiments.shared import native_training_entry

    private, _, candidate = candidate_files(tmp_path)
    sandbox = tmp_path / "sandbox"
    sidecar = training_artifact_candidate_path(
        Path(sandbox_records_dir(str(sandbox))) / "run", "attempt"
    )

    def native_main(*args, **kwargs):
        sidecar.parent.mkdir(parents=True)
        sidecar.write_text(candidate.model_dump_json())

    monkeypatch.setattr(native_training_entry.runpy, "run_module", native_main)
    monkeypatch.setattr(
        native_training_entry.sys,
        "argv",
        [
            "native_training_entry",
            "--model_cfg",
            "model.json",
            "--train_cfg",
            "train.json",
            "--loss_cfg",
            "loss.json",
            "--sandbox_dir",
            str(sandbox),
            "--run_name",
            "run",
            "--exp_id",
            "attempt",
        ],
    )
    native_training_entry.main()
    shutil.rmtree(private)
    result = TrainingArtifactCandidate.model_validate_json(sidecar.read_bytes())
    assert Path(result.model_config_path).is_file()
    assert Path(result.model_plugin_path).is_file()
    assert Path(result.training_scope_path).is_file()
