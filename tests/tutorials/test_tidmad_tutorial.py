"""File-disjoint scientific scopes, source reuse and explicit launch bindings."""

from __future__ import annotations

import pytest
import yaml
from execute_tools.task_data_path import ScopeBuildRequest
from workflows.task_composition import (
    bind_run_task_composition,
    compose_run_task_bindings,
)

from tasks.tidmad.runtime.file_split import FileSplit, sample_population
from tutorials.paper.tidmad.project import create_project, write_file_split_task
from tutorials.paper.tidmad.runner import TidmadExperiment, build_command


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "user project"
    create_project(root, tmp_path / "infra")
    return root


def test_file_partition_refuses_overlap_and_missing_band_members():
    for updates in (
        {"validation_files": (1,)},
        {"test_files": ()},
        {"train_files": (0,)},
        {"train_files": (0, 0, 1)},
        {"test_files": (4,)},
    ):
        with pytest.raises(ValueError):
            FileSplit.model_validate({**FileSplit().model_dump(), **updates})
    split = FileSplit()
    assert set(split.population("train")) == {0, 1}
    assert set(split.population("validation")) == {2}
    assert set(split.population("test")) == {3}
    assert all(rows == list(range(200)) for rows in split.population("train").values())


def test_fraction_uses_each_assigned_file_without_changing_membership():
    split = FileSplit()
    trial = sample_population(split.population("train"), 0.25, 42)
    formal = sample_population(split.population("train"), 0.5, 42)
    assert set(trial) == set(formal) == {0, 1}
    assert sum(map(len, trial.values())) == 100
    assert sum(map(len, formal.values())) == 200
    assert len(sample_population({0: [1, 3, 5]}, 0.5, 42)[0]) == 2


def test_composed_scopes_hold_out_files_and_keep_original_indices(project):
    path = write_file_split_task(project / "tasks/tidmad", FileSplit())
    composition = compose_run_task_bindings(str(path))
    request = ScopeBuildRequest(
        round_kind="trial",
        selection_strategy="snapshot",
        portion=0.25,
        seed=42,
        subset_ref="0,1,2,3",
        task_parameters={"seg_size": 40000},
    )
    with bind_run_task_composition(
        composition, physical_data_root=str(project / "data/band-0-3")
    ):
        adapter = composition.task_data_path
        train, val = (
            adapter.build_training_scope(request),
            adapter.build_eval_scope(request),
        )
        test = adapter.build_final_test_scope()
        assert set(train.sample_set) == {0, 1}
        assert set(val.sample_set) == {2}
        assert test.sample_set == {3: list(range(200))}
        assert sum(map(len, train.sample_set.values())) == 100
        assert len(val.sample_set[2]) == 50
        assert not hasattr(adapter, "build_frozen_training_pool")
        assert (
            adapter.deserialize_scope(adapter.serialize_scope(train)).sample_set
            == train.sample_set
        )
        with pytest.raises(ValueError, match="snapshot"):
            adapter.build_training_scope(
                request.model_copy(update={"selection_strategy": "anchors"})
            )
    changed = yaml.safe_load(path.read_text())
    changed["task_data_path"]["config"]["split"] = FileSplit(
        train_files=(0, 2), validation_files=(1,), test_files=(3,)
    ).model_dump(mode="json")
    path.write_text(yaml.safe_dump(changed))
    assert (
        compose_run_task_bindings(str(path)).semantic_fingerprint
        != composition.semantic_fingerprint
    )


def test_command_uses_selected_file_split_for_health_and_formal_fraction(project):
    settings = TidmadExperiment.model_validate_json(
        (project / "experiments/tidmad-experiment.json").read_text()
    )
    command = build_command(settings)
    assert command[command.index("--formal_portion") + 1] == "0.1"
    assert command[command.index("--ml_lit_review_config") + 1] == str(
        project / "tasks/tidmad/framework_configs/lit_review.yaml"
    )
    assert (
        "--ml_lit_review_enabled" in command and "--no-data_analysis_enabled" in command
    )
    with pytest.raises(ValueError, match="frozen"):
        TidmadExperiment.model_validate(
            {**settings.model_dump(), "formal_train_fraction": 0.5}
        )
    path = write_file_split_task(project / "tasks/tidmad", FileSplit())
    custom = TidmadExperiment.model_validate(
        {
            **settings.model_dump(),
            "protocol": "file-holdout",
            "composition": path,
            "formal_train_fraction": 0.5,
        }
    )
    command = build_command(custom)
    assert command[command.index("--formal_portion") + 1] == "0.5"
    assert command[command.index("--health_gate_files") + 1] == "2"
    assert command[command.index("--formal_train_portion") + 1] == "1.0"
    assert command.count("--formal_portion") == 1
    assert "--retain_training_checkpoints" in command


def test_existing_tidmad_entry_uses_links_and_never_copies_raw(
    project, tmp_path, monkeypatch
):
    from tutorials.paper import data_entry

    source = tmp_path / "shared raw"
    source.mkdir()
    names = {
        f"abra_{family}_{i:04d}.h5"
        for family in ("training", "validation")
        for i in range(4)
    }
    for name in names:
        (source / name).write_bytes(b"original raw bytes")

    def verify(root, manifest, selected):
        assert root == source
        assert selected == names
        return {}

    monkeypatch.setattr(data_entry, "verify_selected_files", verify)
    view = data_entry.use_existing_tidmad(project, source)
    assert all(
        (view / name).is_symlink() and (view / name).resolve() == source / name
        for name in names
    )
    assert all((source / name).read_bytes() == b"original raw bytes" for name in names)
    assert data_entry.use_existing_tidmad(project, source) == view
    link = view / next(iter(names))
    link.unlink()
    link.write_bytes(b"user-owned existing file")
    with pytest.raises(ValueError, match="existing data entry"):
        data_entry.use_existing_tidmad(project, source)
    assert link.read_bytes() == b"user-owned existing file"


def test_project_and_task_write_refuse_overwrite(project):
    with pytest.raises(ValueError, match="fresh"):
        create_project(project, project.parent / "infra")
    write_file_split_task(project / "tasks/tidmad", FileSplit())
    with pytest.raises(FileExistsError):
        write_file_split_task(project / "tasks/tidmad", FileSplit())


def test_final_selection_change_refused_before_test_data(project, monkeypatch):
    from tutorials.paper.tidmad import final_test

    # Resolve in this checkout's environment; this seal test has no installed
    # external infra and must not accidentally use a developer's checkout.
    monkeypatch.setattr(
        final_test,
        "composition_identity",
        lambda _, manifest: compose_run_task_bindings(manifest).semantic_fingerprint,
    )
    settings = TidmadExperiment.model_validate_json(
        (project / "experiments/tidmad-experiment.json").read_text()
    )
    composition = write_file_split_task(project / "tasks/tidmad", FileSplit())
    settings = TidmadExperiment.model_validate(
        {
            **settings.model_dump(),
            "protocol": "file-holdout",
            "composition": composition,
        }
    )
    from agent.schemas.hyperparam_tuning import ExperimentRecord, HyperparamTuningOutput

    model = project / "runs/selected"
    settings = TidmadExperiment.model_validate(
        {**settings.model_dump(), "workspace": model}
    )
    experiment = project / "experiments/holdout.json"
    experiment.write_text(settings.model_dump_json())
    model.mkdir()
    (model / "generated_library").mkdir()
    attempt = model / "attempt"
    (attempt / "cached_models").mkdir(parents=True)
    for name in ("model_config_selected.json", "loss_config_selected.json"):
        (attempt / name).write_text("selected config bytes")
    checkpoint = attempt / "cached_models/model_selected_selected_agent.pth"
    checkpoint.write_text("selected checkpoint bytes")
    (checkpoint.parent / "_OK_selected").touch()
    fingerprint = final_test.composition_identity(settings, str(composition))
    record_path = attempt / "run_output_iter_001.json"
    output_record = HyperparamTuningOutput(
        run_name="iter_001",
        model_type="selected",
        file_index=0,
        status="completed",
        completed_rounds=1,
        total_attempts=1,
        started_at="start",
        finished_at="finish",
        task_composition_fingerprint=fingerprint,
        all_records=[
            ExperimentRecord(
                exp_id="selected",
                status="success",
                model_type="selected",
                timestamp="now",
                params={},
                task_composition_fingerprint=fingerprint,
            )
        ],
    )
    record_path.write_text(output_record.model_dump_json())
    candidate = final_test.candidate_for_record(
        settings, record_path, "selected", search_completed=True
    )
    path = project / "final-test/candidate.json"
    path.write_text(candidate.model_dump_json())
    output = project / "final-test/once"
    monkeypatch.setattr(final_test, "verify_framework_pin", lambda *_: "pinned")
    monkeypatch.setattr(final_test, "verify_installed_framework", lambda *_: None)
    monkeypatch.setattr(
        final_test,
        "verify_band_inputs",
        lambda *_: pytest.fail("must refuse before reading test data"),
    )
    args = [
        "final_test",
        "--experiment",
        str(experiment),
        "--candidate",
        str(path),
        "--output",
        str(output),
    ]
    monkeypatch.setattr("sys.argv", [*args, "--seal"])
    final_test.main()
    assert (output / "selection.json").is_file()
    assert not (output / "test-started.json").exists()
    checkpoint.write_text("changed after model selection")
    monkeypatch.setattr("sys.argv", [*args, "--evaluate"])
    with pytest.raises(ValueError, match="changed after sealing"):
        final_test.main()


def test_launch_requires_exported_credentials_before_data(project, monkeypatch):
    from tutorials.paper.tidmad import runner

    settings = TidmadExperiment.model_validate_json(
        (project / "experiments/tidmad-experiment.json").read_text()
    )
    monkeypatch.setattr(runner, "verify_framework_pin", lambda *_: "pinned")
    monkeypatch.setattr(runner, "verify_installed_framework", lambda *_: None)
    # This case isolates credential refusal; real cross-environment resolution
    # is covered by planner setup checks and saved-script qualification.
    monkeypatch.setattr(runner, "verify_planner_setup", lambda *a, **kw: None)
    monkeypatch.setattr(runner, "composition_identity", lambda *_: "synthetic")
    monkeypatch.setattr(runner.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(
        runner, "credential_status", lambda *_: {"OPENAI_API_KEY": False}
    )
    monkeypatch.setattr(
        runner,
        "verify_band_inputs",
        lambda *_: pytest.fail(
            "missing credentials must refuse before data/GPU checks"
        ),
    )
    with pytest.raises(ValueError, match="export required keys"):
        runner.inspect(settings, launch=True)
    assert not settings.workspace.exists()


def test_native_scope_acquisition_normalizes_band_and_keeps_training_validation_separate(
    project,
):
    from execute_tools.dataset_config import DataScope
    from nodes.ml_hyperparameter_tune_agent.scope_acquisition import (
        acquire_attempt_scopes,
    )

    path = write_file_split_task(project / "tasks/tidmad", FileSplit())
    composition = compose_run_task_bindings(str(path))
    with bind_run_task_composition(
        composition, physical_data_root=str(project / "data/band-0-3")
    ):
        scopes = acquire_attempt_scopes(
            composed=True,
            mode="trial",
            trial_strategy="snapshot",
            trial_portion=0.01,
            eval_strategy="snapshot",
            eval_portion=0.01,
            train_sampling_seed=42,
            eval_sampling_seed=43,
            target_files=None,
            subset=DataScope.from_cli("0-3"),
            validation_max_samples=None,
            task_parameters={"seg_size": 40000},
            training_validation_portion=0.1,
        )
        assert scopes.training.sample_set.keys() == {0, 1}
        assert scopes.evaluation.sample_set.keys() == {2}
        assert scopes.training_validation.sample_set.keys() == {2}
        assert len(scopes.training_validation.sample_set[2]) == 20
        assert len(scopes.evaluation.sample_set[2]) == 2
