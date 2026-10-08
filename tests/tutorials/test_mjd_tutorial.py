"""MJD saved-project defects witnessed with explicitly synthetic HDF5/score fixtures."""

import hashlib
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import h5py
import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from tutorials.shared import saved_run
from tutorials.shared.runtime import ROOT
from tutorials.supplementary.mjd import data, demo, runner
from tutorials.supplementary.mjd.project import (
    create_project,
    save_variant,
    validate_launcher,
)
from tutorials.supplementary.mjd.settings import MjdExperiment


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Small synthetic data only; never silently replace official launch verification."""
    raw = tmp_path / "synthetic raw"
    raw.mkdir()
    manifest = data.DatasetManifest.model_validate_json(
        data.OFFICIAL_MANIFEST.read_text()
    ).model_dump()
    waveform = np.linspace(0, 38, 3800, dtype=np.float32)
    for index, (name, entry) in enumerate(manifest["files"].items()):
        if entry["role"] == "unlabeled":
            continue
        path = raw / name
        with h5py.File(path, "w") as handle:
            handle.create_dataset(
                "raw_waveform", data=np.tile(waveform, (64, 1)), compression="gzip"
            )
            handle["id"] = np.arange(64) + index * 1000
            handle["psd_label_low_avse"] = np.tile([0, 1], 32).astype(np.uint8)
            handle["energy_label"] = np.full(64, 1010, dtype=np.float32)
        entry["bytes"] = path.stat().st_size
        entry["md5"] = hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()
    authority = tmp_path / "synthetic-authority.json"
    authority.write_text(json.dumps(manifest))
    monkeypatch.setattr(data, "OFFICIAL_MANIFEST", authority)
    root = tmp_path / "external project with spaces"
    experiment = create_project(root, ROOT, raw)
    selected = root / "tasks/mjd/declared/dataset_manifest.json"
    selected.write_text(authority.read_text())
    settings = MjdExperiment.model_validate_json(experiment.read_text())
    settings = MjdExperiment.model_validate(
        {
            **settings.model_dump(),
            "trial_train_fraction": 0.5,
            "formal_train_fraction": 1.0,
            "trial_eval_fraction": 0.5,
            "formal_eval_fraction": 1.0,
        }
    )
    experiment.write_text(settings.model_dump_json(indent=2))
    return SimpleNamespace(
        root=root,
        settings=settings,
        experiment=experiment,
        script=root / "scripts/run-mjd.sh",
        authority=authority,
    )


def test_native_arguments_keep_scopes_epochs_and_disabled_treatment_distinct(project):
    settings = MjdExperiment.model_validate(
        {
            **project.settings.model_dump(),
            "iterations": 4,
            "epochs": 2,
            "trial_train_fraction": 0.03,
            "formal_train_fraction": 0.07,
            "trial_eval_fraction": 0.02,
            "formal_eval_fraction": 0.04,
            "trial_minutes": 3,
            "formal_minutes": 6,
            "trial_vram_gib": 8,
            "formal_vram_gib": 9,
        }
    )
    command = runner.build_command(settings)
    expected = {
        "--num_iterations": "4",
        "--max_rounds": "2",
        "--trial_max_epochs": "2",
        "--formal_max_epochs": "2",
        "--trial_portion": "0.03",
        "--formal_portion": "0.07",
        "--eval_portion": "0.02",
        "--formal_eval_portion": "0.04",
        "--train_portion": "1.0",
        "--formal_train_portion": "1.0",
        "--trial_time_budget_minutes": "3.0",
        "--formal_time_budget_minutes": "6.0",
        "--trial_vram_budget_gb": "8.0",
        "--formal_vram_budget_gb": "9.0",
        "--result_authority": "diagnostic",
    }
    for flag, value in expected.items():
        assert command.count(flag) == 1
        assert command[command.index(flag) + 1] == value
    assert json.loads(command[command.index("--plan_overrides") + 1]) == {
        "is_trial": True,
        "trial_strategy": "snapshot",
        "eval_strategy": "snapshot",
    }
    assert (
        "--no-data_analysis_enabled" in command
        and "--no-ml_lit_review_enabled" in command
    )
    assert "--advice" not in command and "--trial_time_admission_source" not in command


def test_real_task_loader_preserves_official_test_role_balance_and_transform(project):
    reports = data.scope_counts(project.settings)
    assert [r.official_role for r in reports] == ["train", "test", "train", "test"]
    assert reports[2].samples == 1024 and reports[3].samples == 384
    assert all(
        r.samples == r.rejected + r.accepted and r.rejected == r.accepted
        for r in reports
    )
    fig = data.show_waveform(project.settings)
    raw = fig.axes[0].lines[0].get_ydata()
    actual = fig.axes[1].lines[0].get_ydata()
    assert len(actual) == 3800 and "Train only" in fig._suptitle.get_text()
    np.testing.assert_allclose(
        actual, (raw - raw[:500].mean()) / max(raw[:500].std(), 1), rtol=1e-6
    )


def test_source_manifest_substitution_and_corrupt_source_bytes_refused(project):
    selected = (
        project.settings.composition.parent.parent / "declared/dataset_manifest.json"
    )
    original = selected.read_text()
    payload = json.loads(original)
    name = "MJD_Train_0.hdf5"
    payload["files"][name]["md5"] = "0" * 32
    selected.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="official task authority"):
        data.verify_files(project.settings)
    selected.write_text(original)
    assert (
        data.verify_files(project.settings, hashes=True)["verification"]
        == "size_and_md5"
    )
    path = project.settings.data_dir / name
    with path.open("r+b") as stream:
        stream.seek(-1, 2)
        stream.write(b"x")
    with pytest.raises(subprocess.CalledProcessError):
        data.verify_files(project.settings, hashes=True)


def test_missing_official_file_refuses_even_for_tiny_fraction(project):
    (project.settings.data_dir / "MJD_Test_5.hdf5").unlink()
    tiny = MjdExperiment.model_validate(
        {**project.settings.model_dump(), "trial_train_fraction": 0.0001}
    )
    with pytest.raises(ValueError, match="all 16 Train and 6 Test"):
        data.verify_files(tiny)


def test_save_as_preserves_original_and_binds_new_json_from_any_cwd(
    project, monkeypatch
):
    before = project.experiment.read_bytes()
    new, script = save_variant(
        project.root, project.experiment, name="mjd-four-001", changes={"iterations": 4}
    )
    validate_launcher(new, script)
    monkeypatch.chdir(project.root.parent)
    subprocess.run(["bash", "-n", str(script)], check=True)
    assert project.experiment.read_bytes() == before
    changed = MjdExperiment.model_validate_json(new.read_text())
    assert changed.iterations == 4 and changed.workspace.name == "mjd-four-001"
    assert "4" in runner.build_command(changed)
    with pytest.raises(ValueError, match="never overwritten"):
        save_variant(project.root, project.experiment, name="mjd-four-001", changes={})
    with pytest.raises(ValueError, match="launcher"):
        validate_launcher(project.experiment, script)


def test_project_alias_and_output_overlap_refused(project, tmp_path):
    alias = tmp_path / "source alias"
    alias.symlink_to(ROOT, target_is_directory=True)
    with pytest.raises(ValueError, match="separate"):
        create_project(alias / "forbidden", ROOT, project.settings.data_dir)
    overlap = MjdExperiment.model_validate(
        {
            **project.settings.model_dump(),
            "workspace": project.settings.data_dir / "run",
        }
    )
    with pytest.raises(ValueError, match="separate from raw data"):
        runner.build_command(overlap)


def test_missing_key_has_no_log_or_workspace_effect(project, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        saved_run,
        "subprocess",
        SimpleNamespace(Popen=lambda *a, **k: pytest.fail("launched without key")),
    )
    with pytest.raises(ValueError, match="Missing exported keys: OPENAI_API_KEY"):
        demo.run_demo(project.experiment, project.script)
    assert not list((project.root / "runs").iterdir())


def test_delegation_uses_saved_script_and_changed_linked_inputs_refuse_reuse(
    project, monkeypatch
):
    calls = []
    monkeypatch.setattr(
        runner, "require_credentials", lambda config: calls.append("credentials")
    )

    def launch(argv, **kwargs):
        calls.append(argv)
        project.settings.workspace.mkdir()
        return SimpleNamespace(wait=lambda timeout: 0)

    monkeypatch.setattr(
        saved_run,
        "subprocess",
        SimpleNamespace(
            Popen=launch,
            STDOUT=subprocess.STDOUT,
            TimeoutExpired=subprocess.TimeoutExpired,
        ),
    )
    first = demo.run_demo(project.experiment, project.script)
    assert calls == ["credentials", ["bash", str(project.script), "--launch"]]
    assert demo.run_demo(project.experiment, project.script) == first
    assert len(calls) == 2
    route = project.settings.llm_config
    route.write_text(route.read_text() + "\n")
    with pytest.raises(ValueError, match="Inputs changed"):
        demo.run_demo(project.experiment, project.script)
    assert len(calls) == 2


def test_no_health_plot_preserves_failed_and_missing_scores(project, tmp_path):
    from tests.tutorials.test_progress_demo import write_record
    from tutorials.shared.progress import read_progress

    workspace = project.settings.workspace
    write_record(workspace, score=0.6, health=False)
    output = next(workspace.rglob("run_output_*.json"))
    payload = json.loads(output.read_text())
    for record in payload["all_records"]:
        record["health_gate_results"] = []
        record["denoising_score"] = 0.6
        record["metric_result"].update(
            metric_id="energy_matched_roc_auc", direction="higher"
        )
    output.write_text(json.dumps(payload))
    assert read_progress(workspace, health_policy="none")[0].validity == "pass"
    figure = demo.plot_results(project.experiment, project.root / "plots/recorded")
    assert "no Health" in figure.axes[0].get_title(loc="left")
    assert (project.root / "plots/recorded/score-versus-iteration.csv").is_file()
    for record in payload["all_records"]:
        record["metric_result"] = None
        record["denoising_score"] = None
    output.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="No measured Formal score"):
        demo.plot_results(project.experiment, project.root / "plots/missing")


@pytest.mark.parametrize("completed", [False, True])
def test_offline_notebook_reads_saved_four_iteration_variant(
    project, tmp_path, completed
):
    """Execute real cells with fixture data; only external effects are disabled."""
    import nbformat
    from jupyter_client import KernelManager
    from nbclient import NotebookClient

    new, script = save_variant(
        project.root, project.experiment, name="mjd-four-001", changes={"iterations": 4}
    )
    notebook = nbformat.read(
        project.root / "notebooks/mjd_tutorial.ipynb", as_version=4
    )
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.source = cell.source.replace(
                'SELECTED_EXPERIMENT = "mjd-demo"',
                'SELECTED_EXPERIMENT = "mjd-four-001"',
            )
            if not completed:
                cell.source = cell.source.replace(
                    "RUN_NATIVE_PREVIEW = True", "RUN_NATIVE_PREVIEW = False"
                )
                cell.source = cell.source.replace(
                    "RUN_QUICK_DEMO = True", "RUN_QUICK_DEMO = False"
                )
    # Isolated kernel receives the same explicit synthetic authority as this test.
    notebook.cells.insert(
        0,
        nbformat.v4.new_code_cell(
            f"import os, sys\nos.chdir({str(ROOT)!r})\n"
            "from pathlib import Path\nfrom tutorials.supplementary.mjd import data\n"
            f"data.OFFICIAL_MANIFEST = Path({str(project.authority)!r})\n"
        ),
    )
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [
        sys.executable,
        "-m",
        "ipykernel_launcher",
        "-f",
        "{connection_file}",
    ]
    env = {
        **os.environ,
        "TUTORIAL_HOME": str(project.root),
        "MPLCONFIGDIR": str(tmp_path / "mpl"),
        "IPYTHONDIR": str(tmp_path / "ipython"),
    }
    client = NotebookClient(
        notebook,
        km=manager,
        timeout=120,
        resources={"metadata": {"path": str(tmp_path)}},
    )
    env.pop("OPENAI_API_KEY", None)
    if completed:
        saved = MjdExperiment.model_validate_json(new.read_text())
        saved.workspace.mkdir()
        receipt = saved.workspace.with_suffix(".notebook-run.json")
        receipt.write_text(
            json.dumps(
                {
                    "input_sha256": demo.input_digest(new, script),
                    "exit_code": 0,
                    "workspace": str(saved.workspace),
                    "log": str(saved.workspace.with_suffix(".console.log")),
                    "elapsed_seconds": 1,
                }
            )
        )
        original = receipt.read_bytes()
    client.execute(env=env)
    if completed:
        # A second Run All must stay on the cache path even with both flags True.
        client.execute(env=env)
        assert receipt.read_bytes() == original
    text = "\n".join(str(c.get("outputs", [])) for c in notebook.cells)
    assert "mjd-four-001" in text
    if completed:
        assert "native launch preview skipped" in text
        assert "Reusing recorded result without API/GPU work" in text
        assert (
            "No measured Formal score" in text
        )  # Empty fixture is never a fabricated chart.
    else:
        assert "Live search disabled" in text
    assert not project.settings.workspace.exists()
    assert MjdExperiment.model_validate_json(new.read_text()).iterations == 4
    validate_launcher(new, script)
