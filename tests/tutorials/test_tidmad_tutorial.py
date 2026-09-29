"""Scientific split and external-project regressions, without provider calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from execute_tools.task_data_path import ScopeBuildRequest
from workflows.task_composition import (
    bind_run_task_composition,
    compose_run_task_bindings,
)

from tasks.tidmad.runtime.frequency_split import (
    FrequencyCatalog,
    FrequencyRow,
    make_split,
    sample_population,
)
from tutorials.paper.tidmad.project import create_project, write_frequency_task
from tutorials.paper.tidmad.runner import TidmadExperiment, build_command


@pytest.fixture
def catalog():
    return FrequencyCatalog(
        source_sha256={
            f"abra_{family}_{i:04d}.h5": "0" * 64
            for family in ("training", "validation")
            for i in range(4)
        },
        rows=tuple(
            FrequencyRow(family=f, file=i, segment=s, frequency_hz=1100 + s % 20 * 100)
            for f in ("training", "validation")
            for i in range(4)
            for s in range(200)
        ),
    )


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "user project"
    create_project(root, Path("/tmp/siderius-tutorial-infra"))
    return root


def test_same_frequency_cannot_cross_splits(catalog):
    split = make_split(catalog)
    sets = [set(split.train_hz), set(split.validation_hz), set(split.test_hz)]
    assert [len(s) for s in sets] == [12, 4, 4]
    assert not sets[0] & sets[1] and not sets[0] & sets[2] and not sets[1] & sets[2]
    for name, family in [
        ("train", "training"),
        ("validation", "validation"),
        ("test", "validation"),
    ]:
        for index, segments in split.population(name).items():
            assert segments == [
                r.segment
                for r in catalog.rows
                if r.family == family
                and r.file == index
                and r.frequency_hz in set(getattr(split, name + "_hz"))
            ]
    data = split.model_dump()
    data["test_hz"] = split.train_hz
    with pytest.raises(ValueError, match="disjoint"):
        type(split).model_validate(data)


def test_missing_or_duplicate_catalog_row_refused(catalog):
    for rows in (catalog.rows[:-1], (*catalog.rows[:-1], catalog.rows[0])):
        with pytest.raises(ValueError, match="exactly once"):
            FrequencyCatalog(source_sha256=catalog.source_sha256, rows=rows)


def test_fraction_is_relative_to_eligible_population(catalog):
    split = make_split(catalog)
    assert {
        len(v) for v in sample_population(split.population("train"), 0.25, 42).values()
    } == {30}
    assert {
        len(v) for v in sample_population(split.population("train"), 0.5, 42).values()
    } == {60}
    assert {
        len(v)
        for v in sample_population(split.population("validation"), 0.5, 42).values()
    } == {20}
    assert (
        sample_population({0: [1, 3, 5]}, 0.5, 42)[0]
        == sample_population({0: [1, 3, 5]}, 0.5, 42)[0]
    )
    assert len(sample_population({0: [1, 3, 5]}, 0.5, 42)[0]) == 2


def test_composed_runtime_excludes_test_and_preserves_original_indices(
    project, catalog
):
    split = make_split(catalog)
    path = write_frequency_task(project / "tasks/tidmad", split)
    composition = compose_run_task_bindings(str(path))
    request = ScopeBuildRequest(
        round_kind="trial",
        selection_strategy="snapshot",
        portion=0.25,
        seed=42,
        subset_ref="0-3",
        task_parameters={"seg_size": 40000},
    )
    with bind_run_task_composition(
        composition, physical_data_root=str(project / "data/band-0-3")
    ):
        adapter = composition.task_data_path
        train = adapter.build_training_scope(request)
        val = adapter.build_eval_scope(request)
        assert {len(v) for v in train.sample_set.values()} == {30}
        assert {len(v) for v in val.sample_set.values()} == {10}
        assert not hasattr(adapter, "build_frozen_training_pool")
        for i in range(4):
            assert set(train.sample_set[i]) <= set(split.population("train")[i])
            assert set(val.sample_set[i]) <= set(split.population("validation")[i])
            assert not set(val.sample_set[i]) & set(split.population("test")[i])
        restored = adapter.deserialize_scope(adapter.serialize_scope(train))
        assert restored.sample_set == train.sample_set
        with pytest.raises(ValueError, match="snapshot"):
            adapter.build_training_scope(
                request.model_copy(update={"selection_strategy": "anchors"})
            )
    changed = yaml.safe_load(path.read_text())
    changed["task_data_path"]["config"]["split"] = make_split(
        catalog, seed=43
    ).model_dump(mode="json")
    path.write_text(yaml.safe_dump(changed))
    assert (
        compose_run_task_bindings(str(path)).semantic_fingerprint
        != composition.semantic_fingerprint
    )


def test_paper_and_frequency_commands(project, catalog):
    settings = TidmadExperiment.model_validate_json(
        (project / "experiments/tidmad-experiment.json").read_text()
    )
    command = build_command(settings)
    assert command[command.index("--formal_portion") + 1] == "0.1"
    assert command[command.index("--trial_portion") + 1] == "0.5"
    assert "--ml_lit_review_enabled" in command
    assert "--no-data_analysis_enabled" in command
    assert (
        "--no-human_advice_enabled" not in command
    )  # Treatment uses absence, not an invented CLI flag.
    with pytest.raises(ValueError, match="frozen"):
        TidmadExperiment.model_validate(
            {**settings.model_dump(), "formal_train_fraction": 0.5}
        )
    path = write_frequency_task(project / "tasks/tidmad", make_split(catalog))
    custom = TidmadExperiment.model_validate(
        {
            **settings.model_dump(),
            "protocol": "frequency-holdout",
            "composition": path,
            "formal_train_fraction": 0.5,
        }
    )
    command = build_command(custom)
    assert command[command.index("--formal_portion") + 1] == "0.5"
    assert command.count("--formal_portion") == 1
    assert command[command.index("--formal_train_portion") + 1] == "1.0"
    with pytest.raises(ValueError, match="frozen"):
        TidmadExperiment.model_validate(
            {**settings.model_dump(), "formal_train_fraction": 0.2}
        )


def test_project_no_overwrite_and_source_unchanged(project):
    assert (
        "tutorials.paper.tidmad.runner"
        in (project / "scripts/run-tidmad.sh").read_text()
    )
    assert json.loads((project / "project.json").read_text())[
        "default_experiment"
    ].startswith(str(project))
    with pytest.raises(ValueError, match="fresh"):
        create_project(project, Path("/tmp/siderius-tutorial-infra"))


def test_final_selection_change_refused_before_test_data(project, catalog, monkeypatch):
    from tutorials.paper.tidmad import final_test

    settings = TidmadExperiment.model_validate_json(
        (project / "experiments/tidmad-experiment.json").read_text()
    )
    composition = write_frequency_task(project / "tasks/tidmad", make_split(catalog))
    settings = TidmadExperiment.model_validate(
        {
            **settings.model_dump(),
            "protocol": "frequency-holdout",
            "composition": composition,
            "catalog_reviewed": True,
        }
    )
    experiment = project / "experiments/holdout.json"
    experiment.write_text(settings.model_dump_json())
    model = project / "runs/selected"
    model.mkdir()
    (model / "generated_library").mkdir()
    for name in ("weights.pth", "model.json", "loss.json", "_OK_selected"):
        (model / name).write_text("selected bytes")
    candidate = final_test.Candidate(
        model_name="selected",
        exp_id="selected",
        checkpoint=model / "weights.pth",
        model_config_path=model / "model.json",
        loss_config_path=model / "loss.json",
        generated_library=model / "generated_library",
        search_completed=True,
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
    (model / "weights.pth").write_text("changed after model selection")
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
