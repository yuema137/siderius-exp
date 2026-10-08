"""Cancer teaching boundaries exercised with explicitly synthetic graph fixtures."""

import hashlib
import json
import os
from types import SimpleNamespace

import h5py
import matplotlib
import numpy as np
import pytest
import yaml

matplotlib.use("Agg")

from tutorials.shared.runtime import ROOT
from tutorials.supplementary.cancer import data, demo, runner
from tutorials.supplementary.cancer.project import (
    create_project,
    save_variant,
    validate_launcher,
)
from tutorials.supplementary.cancer.settings import CancerExperiment


@pytest.fixture
def project(tmp_path, monkeypatch):
    raw = tmp_path / "raw data"
    file = raw / "cpdb/data.h5"
    file.parent.mkdir(parents=True)
    with h5py.File(file, "w") as handle:
        handle["features"] = np.arange(20 * 64, dtype=np.float32).reshape(20, 64)
        network = np.eye(20, dtype=np.float64)
        network[np.arange(19), np.arange(1, 20)] = 1
        handle["network"] = network
        for split, start, stop in (("train", 0, 10), ("val", 10, 16), ("test", 16, 20)):
            mask = np.zeros(20, dtype=np.int8)
            mask[start:stop] = 1
            handle[f"mask_{split}"] = mask
            if split != "test":
                handle[f"y_{split}"] = np.arange(20, dtype=np.float32) % 2
    source = json.loads(data.SOURCE_MANIFEST.read_text())
    source.update(
        bytes=file.stat().st_size, sha256=hashlib.sha256(file.read_bytes()).hexdigest()
    )
    authority = tmp_path / "synthetic authority.json"
    authority.write_text(json.dumps(source))
    monkeypatch.setattr(data, "SOURCE_MANIFEST", authority)
    home = tmp_path / "external project with spaces"
    experiment = create_project(home, ROOT, raw)
    (home / "tasks/cancer/declared/tutorial_source_files.json").write_text(
        authority.read_text()
    )
    return SimpleNamespace(
        home=home,
        experiment=experiment,
        script=home / "scripts/run-cancer.sh",
        raw=file,
        settings=CancerExperiment.model_validate_json(experiment.read_text()),
    )


def test_native_parser_receives_effective_label_controls_and_full_graph_scopes(project):
    from workflows.standard_cli import build_parser, normalize_args

    changed = CancerExperiment.model_validate(
        {
            **project.settings.model_dump(),
            "trial_train_label_fraction": 0.25,
            "trial_eval_label_fraction": 0.5,
            "formal_train_label_fraction": 0.75,
        }
    )
    args = runner.build_command(changed)[2:]
    for flag, width in (
        ("--mode", 2),
        ("--num_iterations", 2),
        ("--no_auto_resume", 1),
    ):
        index = args.index(flag)
        del args[index : index + width]
    parsed = normalize_args(
        build_parser().parse_args([*args, "--start_iteration", "1"])
    )
    assert parsed.trial_portion == parsed.formal_portion == 1
    assert parsed.train_portion == 0.25 and parsed.formal_train_portion == 0.75
    assert parsed.eval_portion == 0.5 and parsed.formal_eval_portion == 1
    assert parsed.formal_training_scope_source == "operator"
    assert parsed.allowed_output_types == "regressor"
    assert parsed.max_rounds == 2 and parsed.max_epochs == 1
    assert not project.settings.workspace.exists()


def test_actual_task_loader_changes_only_active_label_columns(project):
    full, target = data.materialize(project.settings, role="train", fraction=1)
    reduced, reduced_target = data.materialize(
        project.settings, role="train", fraction=0.25
    )
    assert full.shape == reduced.shape == (39, 68)
    np.testing.assert_array_equal(
        full[:, [0, 1, 2, *range(4, 68)]], reduced[:, [0, 1, 2, *range(4, 68)]]
    )
    assert int((target[:, 1] == 1).sum()) == 10
    assert int((reduced_target[:, 1] == 1).sum()) == 3
    assert not ((reduced_target[:, 1] == 1) & (target[:, 1] != 1)).any()
    _, validation = data.materialize(project.settings, role="validation", fraction=0.5)
    assert int((validation[:, 1] == 1).sum()) == 3
    assert not ((validation[:, 1] == 1) & (target[:, 1] == 1)).any()
    path = data.selected_task(project.settings)
    assert path.max_inference_batch_size() == 1
    counts = data.scope_counts(project.settings)
    assert [c.active_labels for c in counts] == [10, 6, 10, 6]
    figure = data.show_graph(project.settings)
    assert "Train" in figure.axes[0].get_title()
    assert "Visualization only" in figure.axes[1].get_title()
    with pytest.raises(ValueError, match="test labels remain unused"):
        data.materialize(project.settings, role="test", fraction=1)


def test_native_epoch_fraction_really_overrides_training_scope(project):
    from execute_tools.task_data_path import EpochSamplingParams, ScopeBuildRequest

    path = data.selected_task(project.settings)
    scope = path.build_training_scope(
        ScopeBuildRequest(
            round_kind="trial", selection_strategy="snapshot", portion=0.25, seed=42
        )
    )
    _, target = path.training_dataset(
        scope,
        EpochSamplingParams(data_dir=str(project.settings.data_dir), train_portion=1),
    )[0]
    assert int((target[:, 1] == 1).sum()) == 10


@pytest.mark.parametrize(
    "field",
    [
        "trial_train_label_fraction",
        "formal_train_label_fraction",
        "trial_eval_label_fraction",
        "formal_eval_label_fraction",
    ],
)
def test_below_native_fraction_floor_refuses_before_saving(project, field):
    with pytest.raises(ValueError, match="greater than or equal to 0.01"):
        save_variant(
            project.home, project.experiment, name="bad", changes={field: 0.005}
        )
    assert not (project.home / "experiments/bad.json").exists()


def test_initialization_clears_outputs_and_variant_keeps_original(project):
    original = project.experiment.read_bytes()
    experiment, script = save_variant(
        project.home, project.experiment, name="four", changes={"iterations": 4}
    )
    validate_launcher(experiment, script)
    assert project.experiment.read_bytes() == original
    assert (
        CancerExperiment.model_validate_json(experiment.read_text()).workspace
        == project.home / "runs/four"
    )
    copied = json.loads((project.home / "notebooks/cancer_tutorial.ipynb").read_text())
    assert all(
        not c["outputs"] and c["execution_count"] is None
        for c in copied["cells"]
        if c["cell_type"] == "code"
    )
    assert "SELECTED_EXPERIMENT" in "".join(copied["cells"][1]["source"])
    with pytest.raises(ValueError, match="never overwritten"):
        save_variant(project.home, project.experiment, name="four", changes={})


def test_source_identity_and_raw_mutation_invalidate_reuse(project):
    digest = demo.input_digest(project.experiment, project.script)
    stamp = project.raw.stat()
    os.utime(project.raw, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1))
    assert demo.input_digest(project.experiment, project.script) != digest
    assert (
        data.verify_files(project.settings, hashes=True)["verification"]
        == "sha256_and_structure"
    )
    with project.raw.open("r+b") as stream:
        stream.seek(-1, 2)
        original = stream.read(1)
        stream.seek(-1, 2)
        stream.write(bytes([original[0] ^ 1]))
    with pytest.raises(ValueError, match="SHA-256"):
        data.verify_files(project.settings, hashes=True)


def test_mutated_manifest_and_bad_masks_refuse(project):
    manifest = project.home / "tasks/cancer/declared/tutorial_source_files.json"
    original = manifest.read_text()
    manifest.write_text(original.replace('"bytes":', '"bytes": 1, "duplicate":'))
    with pytest.raises(ValueError):
        data.verify_files(project.settings)
    manifest.write_text(original)
    with h5py.File(project.raw, "r+") as handle:
        handle["mask_val"][0] = 1
    with pytest.raises(ValueError, match="overlap"):
        data.verify_files(project.settings)


@pytest.mark.parametrize("changed", ["test", "network", "batch"])
def test_scope_expansion_is_explicitly_refused(project, changed):
    composition = project.settings.composition
    content = yaml.safe_load(composition.read_text())
    if changed == "test":
        content["task_data_path"]["config"]["evaluation_split"] = "test"
    elif changed == "network":
        content["task_data_path"]["config"]["instances"] = ["ltg"]
    else:
        content["parameter_rules"]["train_config.batch_size"] = {"exact": 2}
    composition.write_text(yaml.safe_dump(content))
    with pytest.raises(ValueError):
        data.selected_task(project.settings)


def test_copied_task_contract_matches_original_forward_contract():
    declarations = ROOT / "tasks/cancer_gene_identification/declared"
    original = yaml.safe_load((declarations / "task_config.yaml").read_text())
    tutorial = yaml.safe_load((declarations / "tutorial_task_config.yaml").read_text())
    assert original["forward_contract"] == tutorial["forward_contract"]
    assert "complete CPDB" in tutorial["task_description"]


def test_missing_credentials_refuse_before_gpu_or_native_exec(project, monkeypatch):
    monkeypatch.setattr(runner, "verify_framework_pin", lambda *a: "a" * 40)
    monkeypatch.setattr(runner, "verify_installed_framework", lambda *a: None)
    monkeypatch.setattr(runner, "verify_planner_setup", lambda *a, **kw: None)
    monkeypatch.setattr(runner, "composition_identity", lambda *a: "b" * 64)
    monkeypatch.setattr(
        runner, "credential_status", lambda *a: {"OPENAI_API_KEY": False}
    )
    monkeypatch.setattr(runner.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(runner, "verify_gpu", lambda *a: pytest.fail("GPU before keys"))
    with pytest.raises(ValueError, match="Missing exported keys"):
        runner.inspect(project.settings, launch=True)
    assert not project.settings.workspace.exists()


def test_completed_reuse_needs_no_key_and_changed_saved_input_refuses(
    project, monkeypatch
):
    settings = project.settings
    settings.workspace.mkdir()
    receipt = settings.workspace.with_suffix(".notebook-run.json")
    result = {
        "input_sha256": demo.input_digest(project.experiment, project.script),
        "exit_code": 0,
        "workspace": str(settings.workspace),
    }
    receipt.write_text(json.dumps(result))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert demo.run_demo(project.experiment, project.script) == result
    changed = settings.model_dump(mode="json")
    changed["iterations"] = 4
    project.experiment.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="changed"):
        demo.run_demo(project.experiment, project.script)
    assert json.loads(receipt.read_text()) == result


def test_source_aliases_are_not_user_project_locations(project):
    with pytest.raises(ValueError, match="separate"):
        create_project(ROOT / "illegal-project", ROOT, project.settings.data_dir)
    with pytest.raises(ValueError, match="separate"):
        create_project(
            project.settings.data_dir / "illegal-project",
            ROOT,
            project.settings.data_dir,
        )


def test_no_health_plot_does_not_invent_missing_score_or_fill_failed_point(project):
    from tests.tutorials.test_progress_demo import write_record

    output = write_record(
        project.settings.workspace, score=0.6, status="failed_mode_collapse"
    )
    payload = json.loads(output.read_text())
    for record in payload["all_records"]:
        record["health_gate_results"] = []
        record["denoising_score"] = 0.6
        record["metric_result"]["metric_id"] = "mean_auprc"
    output.write_text(json.dumps(payload))
    figure = demo.plot_results(project.experiment, project.home / "plots/failed")
    assert list(figure.axes[0].collections[0].get_facecolors()[0]) == [1, 1, 1, 1]
    for record in payload["all_records"]:
        record["metric_result"] = None
        record["denoising_score"] = None
    output.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="No measured Formal score"):
        demo.plot_results(project.experiment, project.home / "plots/missing")


def test_resolved_cpdb_prompt_and_profile_do_not_request_eight_networks(project):
    from workflows.task_composition import compose_run_task_bindings

    binding = compose_run_task_bindings(str(project.settings.composition))
    assert binding.dataset_profile.partition_count == 1
    assert binding.dataset_profile.topology["instances"] == ["cpdb"]
    blocks = binding.proposal_blocks.model_dump()
    assert "complete selected CPDB" in blocks["per_file_strategy_guidance"]
    assert "eight" not in json.dumps(blocks).lower()
    assert "most others" not in blocks["evidence_reading"]
    assert "complete CPDB" in binding.task_description
    assert "eight" not in binding.implementor_blocks.model_dump_json().lower()
