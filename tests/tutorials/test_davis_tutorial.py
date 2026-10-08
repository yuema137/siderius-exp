"""DAVIS external-project boundaries; synthetic JPEGs, no API/GPU/downloads."""

import hashlib
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import matplotlib
import pytest
import yaml
from PIL import Image

matplotlib.use("Agg")

from tutorials.shared.runtime import ROOT
from tutorials.supplementary.davis import data, demo, runner
from tutorials.supplementary.davis.project import (
    create_project,
    save_variant,
    validate_launcher,
)
from tutorials.supplementary.davis.settings import DavisExperiment


@pytest.fixture
def project(tmp_path):
    raw = tmp_path / "raw data"
    raw.mkdir()
    (raw / data.DAVIS_TRAINVAL_480P.name).write_bytes(
        b"explicit synthetic archive fixture"
    )
    home = tmp_path / "external project with spaces"
    experiment = create_project(home, ROOT, raw)
    settings = DavisExperiment.model_validate_json(experiment.read_text())
    # Use native committed identity parsing, not an independent fixture split.
    for index, path in enumerate(data.frame_files(settings)):
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (12, 8), (index % 256, 40, 180)).save(path)
    return SimpleNamespace(
        home=home,
        experiment=experiment,
        script=home / "scripts/run-davis.sh",
        raw=raw,
        settings=settings,
    )


def test_native_parser_uses_clip_scope_and_full_epoch_sampling(project):
    from workflows.standard_cli import build_parser, normalize_args

    changed = DavisExperiment.model_validate(
        {
            **project.settings.model_dump(),
            "formal_train_fraction": 0.75,
            "trial_eval_fraction": 0.5,
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
    assert parsed.trial_portion == 0.25 and parsed.formal_portion == 0.75
    assert parsed.train_portion == parsed.formal_train_portion == 1
    assert parsed.eval_portion == 0.5 and parsed.formal_eval_portion == 1
    assert parsed.formal_training_scope_source == "operator"
    assert parsed.max_rounds == 2 and parsed.max_epochs == 1
    assert "--vram_preflight_host_memory_limit_gb" not in args
    assert not project.settings.workspace.exists()


def test_repeated_composition_preview_uses_one_decoder_registration(project):
    from execute_tools.task_data_path import EpochSamplingParams, ScopeBuildRequest

    for _ in range(2):
        task = data.selected_task(project.settings)
        counts = data.scope_counts(project.settings)
        assert [c.clips for c in counts] == [15, 15, 30, 15]
        request = ScopeBuildRequest(
            round_kind="trial", selection_strategy="snapshot", portion=0.25, seed=42
        )
        train = task.build_training_scope(request)
        validation = task.build_eval_scope(request)
        assert not {r.sequence_name for r in train.rows} & {
            r.sequence_name for r in validation.rows
        }
        x, y = task.training_dataset(
            train, EpochSamplingParams(data_dir=str(project.raw), train_portion=1)
        )[0]
        assert tuple(x.shape) == (3, 8, 128, 224) and tuple(y.shape) == (3, 4, 128, 224)
        assert 0 <= float(x.min()) <= float(x.max()) <= 1
        with pytest.raises(ValueError, match="fractional-epoch"):
            task.training_dataset(
                train, EpochSamplingParams(data_dir=str(project.raw), train_portion=0.5)
            )
    figure = data.show_clip(project.settings)
    assert len(figure.axes) == 12
    assert figure.axes[7].get_title() == "Context 8"
    assert figure.axes[8].get_title() == "Target 1"


def test_frozen_manifest_missing_frame_and_data_replacement_fail_closed(project):
    data.verify_files(project.settings)
    old = demo.input_digest(project.experiment, project.script)
    raw = data.frame_files(project.settings)[0]
    stamp = raw.stat()
    os.utime(raw, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1))
    assert demo.input_digest(project.experiment, project.script) != old
    raw.unlink()
    with pytest.raises(ValueError, match="Missing or empty DAVIS frame"):
        data.verify_files(project.settings)
    manifest = data.manifests(project.settings) / "gate2_train.csv"
    manifest.write_text(
        manifest.read_text().replace("bear,0,train", "bear,0,validation")
    )
    with pytest.raises(ValueError, match="differs from the original"):
        data.verify_files(project.settings)


def test_archive_and_decoded_probe_checks_are_separate(project, monkeypatch):
    from dataclasses import replace

    with pytest.raises(ValueError, match="archive SHA-256"):
        data.verify_files(project.settings, hashes=True)
    archive = project.raw / data.DAVIS_TRAINVAL_480P.name
    monkeypatch.setattr(
        data,
        "DAVIS_TRAINVAL_480P",
        replace(
            data.DAVIS_TRAINVAL_480P,
            sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        ),
    )
    with pytest.raises(ValueError, match="decoded-window probe"):
        data.verify_files(project.settings, hashes=True)


def test_changed_final_scope_and_health_refuse(project):
    path = project.settings.composition
    original = path.read_text()
    content = yaml.safe_load(original)
    content["task_data_path"]["config"]["eval_clips_path"]["ref"] = (
        "../data/manifests/gate2_final.csv"
    )
    path.write_text(yaml.safe_dump(content))
    with pytest.raises(ValueError, match="Final clips remain unbound"):
        data.selected_task(project.settings)
    path.write_text(original)
    health = project.home / "tasks/davis/declared/task_health.yaml"
    health.write_text(
        health.read_text().replace("min_dispersion: 0.04", "min_dispersion: 0.0")
    )
    with pytest.raises(ValueError, match="differs from the original"):
        data.verify_files(project.settings)


@pytest.mark.parametrize(
    "field",
    [
        "trial_train_fraction",
        "formal_train_fraction",
        "trial_eval_fraction",
        "formal_eval_fraction",
    ],
)
def test_below_native_fraction_floor_refuses_before_save(project, field):
    with pytest.raises(ValueError, match="greater than or equal to 0.01"):
        save_variant(
            project.home, project.experiment, name="bad", changes={field: 0.005}
        )
    assert not (project.home / "experiments/bad.json").exists()


def test_variant_initialization_and_reuse_preserve_evidence(project, monkeypatch):
    old = project.experiment.read_bytes()
    changed, script = save_variant(
        project.home,
        project.experiment,
        name="four",
        changes={"iterations": 4, "formal_train_fraction": 0.75},
    )
    validate_launcher(changed, script)
    assert project.experiment.read_bytes() == old
    assert (
        DavisExperiment.model_validate_json(changed.read_text()).workspace
        == project.home / "runs/four"
    )
    copied = json.loads((project.home / "notebooks/davis_tutorial.ipynb").read_text())
    assert all(
        c["execution_count"] is None and not c["outputs"]
        for c in copied["cells"]
        if c["cell_type"] == "code"
    )
    with pytest.raises(ValueError, match="never overwritten"):
        save_variant(project.home, project.experiment, name="four", changes={})
    workspace = project.settings.workspace
    workspace.mkdir()
    result = {
        "input_sha256": demo.input_digest(project.experiment, project.script),
        "exit_code": 0,
        "workspace": str(workspace),
    }
    receipt = workspace.with_suffix(".notebook-run.json")
    receipt.write_text(json.dumps(result))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert demo.run_demo(project.experiment, project.script) == result
    project.experiment.write_text(
        old.decode().replace('"iterations": 3', '"iterations": 4')
    )
    with pytest.raises(ValueError, match="changed"):
        demo.run_demo(project.experiment, project.script)
    assert json.loads(receipt.read_text()) == result


def test_keys_refuse_before_gpu_or_launch(project, monkeypatch):
    monkeypatch.setattr(runner, "verify_framework_pin", lambda *a: "a" * 40)
    monkeypatch.setattr(runner, "verify_installed_framework", lambda *a: None)
    monkeypatch.setattr(runner, "verify_planner_setup", lambda *a, **kw: None)
    monkeypatch.setattr(runner, "composition_identity", lambda *a: "b" * 64)
    monkeypatch.setattr(
        runner, "credential_status", lambda *a: {"OPENAI_API_KEY": False}
    )
    monkeypatch.setattr(runner.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(
        runner, "verify_gpu", lambda *a: pytest.fail("GPU before credentials")
    )
    with pytest.raises(ValueError, match="Missing exported keys"):
        runner.inspect(project.settings, launch=True)
    assert not project.settings.workspace.exists()


def test_plot_keeps_failed_health_hollow_and_mse_lower(project):
    from tests.tutorials.test_progress_demo import write_record

    path = write_record(
        project.settings.workspace,
        score=0.2,
        health=False,
        status="failed_mode_collapse",
    )
    payload = json.loads(path.read_text())
    for record in payload["all_records"]:
        record["metric_result"].update(metric_id="mse", direction="lower")
    path.write_text(json.dumps(payload))
    figure = demo.plot_results(project.experiment, project.home / "plots/failed")
    assert list(figure.axes[0].collections[0].get_facecolors()[0]) == [1, 1, 1, 1]
    for record in payload["all_records"]:
        record["metric_result"] = None
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="No measured Formal score"):
        demo.plot_results(project.experiment, project.home / "plots/missing")


def test_fetch_rejects_repository_root_before_any_fetch(tmp_path):
    # Isolated process prevents the owning tool's normal-package import from
    # sharing the tutorial composition registry. No network is allowed here.
    code = """
from pathlib import Path
from tasks.davis_future_prediction.tools import fetch_davis as f
f.verify_or_fetch=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('fetch reached'))
f.main(['--dest',str(Path.cwd()/'illegal-data'),'--no-download'])
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2 and "outside" in result.stderr
    assert "fetch reached" not in result.stderr


def test_fetch_check_layout_reaches_committed_manifest_without_download(tmp_path):
    code = """
import sys
from pathlib import Path
from tasks.davis_future_prediction.tools import fetch_davis as f
f.verify_or_fetch=lambda *a,**kw: None
seen=[]
f.check_layout=lambda dest,names: seen.extend(names)
assert f.main(['--dest',sys.argv[1],'--no-download','--check-layout'])==0
assert len(seen)==90 and 'bear' in seen and 'blackswan' in seen
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path / "raw")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_changed_forward_tensor_contract_refuses_before_effects(project):
    config = project.home / "tasks/davis/declared/task_config.yaml"
    original = yaml.safe_load(config.read_text())
    original["forward_contract"]["model_io"]["output"]["axes"][2]["dimension"][
        "fixed"
    ] = 8
    config.write_text(yaml.safe_dump(original))
    with pytest.raises(ValueError, match="original 8-context/4-target"):
        data.selected_task(project.settings)


def test_edited_task_description_requires_fresh_notebook_process(project):
    config = project.home / "tasks/davis/declared/task_config.yaml"
    values = yaml.safe_load(config.read_text())
    values["task_description"] += " Additional user context."
    config.write_text(yaml.safe_dump(values))
    with pytest.raises(ValueError, match="restart the process"):
        data.selected_task(project.settings)


@pytest.mark.parametrize("change,expected_code", [("description", 0), ("output", 1)])
def test_fresh_process_accepts_description_but_refuses_changed_shape(
    project, change, expected_code
):
    config = project.home / "tasks/davis/declared/task_config.yaml"
    values = yaml.safe_load(config.read_text())
    if change == "description":
        values["task_description"] += " Additional user context."
    else:
        values["forward_contract"]["model_io"]["output"]["axes"][2]["dimension"][
            "fixed"
        ] = 8
        # Keep shapes internally consistent; the native objective snapshot
        # must still reject a changed original task contract.
        values["forward_contract"]["supervision_target"]["axes"][2]["dimension"][
            "fixed"
        ] = 8
    config.write_text(yaml.safe_dump(values))
    code = """
import sys
from pathlib import Path
from tutorials.supplementary.davis.data import selected_task
from tutorials.supplementary.davis.settings import DavisExperiment
selected_task(DavisExperiment.model_validate_json(Path(sys.argv[1]).read_text()))
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(project.experiment)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == expected_code, result.stdout + result.stderr
    if expected_code:
        assert "objective contract metadata refused" in result.stderr


def test_notebook_save_cell_selects_variant_for_review_launch_and_plot(
    project, monkeypatch
):
    notebook = json.loads(
        (ROOT / "tutorials/supplementary/davis/davis_tutorial.ipynb").read_text()
    )
    namespace = {
        "PROJECT": project.home,
        "EXPERIMENT": project.experiment,
        "SCRIPT": project.script,
        "save_variant": save_variant,
        "DavisExperiment": DavisExperiment,
    }
    save_cell = "".join(notebook["cells"][6]["source"]).replace(
        "SAVE_VARIANT = False", "SAVE_VARIANT = True"
    )
    exec(compile(save_cell, "notebook-save-cell", "exec"), namespace)  # noqa: S102 - repository-owned cell
    selected = DavisExperiment.model_validate_json(namespace["EXPERIMENT"].read_text())
    assert (
        selected.iterations == 4
        and selected.workspace == project.home / "runs/davis-four-001"
    )
    assert namespace["SCRIPT"] == project.home / "scripts/run-davis-four-001.sh"
    assert "davis-four-001.json" in demo.review(
        namespace["EXPERIMENT"], namespace["SCRIPT"]
    )
    native = runner.build_command(selected)
    assert native[native.index("--num_iterations") + 1] == "4"
    calls = []
    namespace["run_demo"] = lambda experiment, script, **kw: (
        calls.append((experiment, script)) or {"exit_code": 0}
    )
    exec(  # noqa: S102 - repository-owned cell with mocked execution
        compile("".join(notebook["cells"][10]["source"]), "notebook-run-cell", "exec"),
        namespace,
    )
    assert calls == [(namespace["EXPERIMENT"], namespace["SCRIPT"])]
    assert namespace["EXPERIMENT"] != project.experiment
    # Plot target is established before the notebook's workspace-existence branch.
    namespace["plot_results"] = lambda *a: pytest.fail("no completed workspace exists")
    exec(  # noqa: S102 - repository-owned cell with mocked execution
        compile("".join(notebook["cells"][12]["source"]), "notebook-plot-cell", "exec"),
        namespace,
    )
    assert namespace["PLOT_EXPERIMENT"] == namespace["EXPERIMENT"]
    assert namespace["plot_settings"].iterations == 4
