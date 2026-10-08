"""SuperNEMO tutorial handoff regressions, with explicitly synthetic event data."""

import json
import os
import subprocess
import sys
from types import SimpleNamespace

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from tests.tutorials.test_supernemo_preparation import fixture_data  # noqa: F401
from tutorials.shared.runtime import ROOT
from tutorials.supplementary.supernemo import data, demo, prepare, runner
from tutorials.supplementary.supernemo.project import (
    create_project,
    save_variant,
    validate_launcher,
)
from tutorials.supplementary.supernemo.settings import SuperNemoExperiment

_REAL_RUN = subprocess.run


@pytest.fixture
def project(fixture_data, tmp_path, monkeypatch):  # noqa: F811 -- imported pytest fixture
    raw, prepared, _ = fixture_data
    prepare.prepare(raw, prepared)
    monkeypatch.setattr(subprocess, "run", _REAL_RUN)
    monkeypatch.setattr(data, "SOURCE_MANIFEST", prepare.SOURCE_MANIFEST)
    project = tmp_path / "external project with spaces"
    experiment = create_project(project, ROOT, prepared)
    selected = project / "tasks/supernemo/declared/source_files.json"
    selected.write_text(prepare.SOURCE_MANIFEST.read_text())
    settings = SuperNemoExperiment.model_validate_json(experiment.read_text())
    return SimpleNamespace(
        root=project,
        experiment=experiment,
        settings=settings,
        script=project / "scripts/run-supernemo.sh",
        authority=prepare.SOURCE_MANIFEST,
    )


def test_default_native_argv_accepted_by_actual_iteration_parser(project):
    from workflows.standard_cli import build_parser, normalize_args

    arguments = runner.build_command(project.settings)[2:]
    for flag, width in (
        ("--mode", 2),
        ("--num_iterations", 2),
        ("--no_auto_resume", 1),
    ):
        at = arguments.index(flag)
        del arguments[at : at + width]
    arguments.extend(["--start_iteration", "1"])
    parsed = normalize_args(build_parser().parse_args(arguments))
    assert (
        parsed.trial_portion
        == parsed.eval_portion
        == parsed.formal_portion
        == parsed.formal_eval_portion
        == 0.01
    )
    assert parsed.train_portion == parsed.formal_train_portion == 1
    assert parsed.max_rounds == 2 and parsed.max_epochs == 1
    assert not parsed.ml_lit_review_enabled and not parsed.data_analysis_enabled
    assert not project.settings.workspace.exists()


@pytest.mark.parametrize(
    "field",
    [
        "trial_train_fraction",
        "trial_eval_fraction",
        "formal_train_fraction",
        "formal_eval_fraction",
    ],
)
def test_invalid_fraction_refuses_save_before_files(project, field):
    with pytest.raises(ValueError, match="greater than or equal to 0.01"):
        save_variant(
            project.root,
            project.experiment,
            name="bad-fraction",
            changes={field: 0.005},
        )
    assert not (project.root / "experiments/bad-fraction.json").exists()


def test_native_task_counts_and_figure_never_select_test(project):
    from execute_tools.task_data_path import EpochSamplingParams, ScopeBuildRequest

    path = data.selected_task(project.settings)
    dataset = path.training_dataset(
        path.build_training_scope(
            ScopeBuildRequest(
                round_kind="trial", selection_strategy="snapshot", portion=1, seed=42
            )
        ),
        EpochSamplingParams(data_dir=str(project.settings.data_dir), train_portion=1),
    )
    for pid, event_index in zip(
        dataset.events.process_ids, dataset.events.event_indices, strict=True
    ):
        process = prepare.PROCESSES[int(pid)]
        with np.load(
            project.settings.data_dir / f"event_indexes/{process}_event_index.npz"
        ) as index:
            assert index["splits"][event_index] == 0
    counts = data.scope_counts(project.settings)
    assert [r.role for r in counts] == ["train", "validation", "train", "validation"]
    assert all(c.background == c.signal and c.samples > 0 for c in counts)
    fig = data.show_event(project.settings)
    assert fig.axes[0].get_xlabel() == "Task-scaled tX"
    assert "data_" in fig.axes[0].get_title() and "event" in fig.axes[0].get_title()
    values = np.asarray(fig.axes[1].images[0].get_array())
    assert values.shape == (224, 11) and values[:, 0].sum() == 2
    assert np.all(values[2:] == 0)


def test_named_variant_preserves_original_and_script_bindings(
    project, tmp_path, monkeypatch
):
    before = project.experiment.read_bytes()
    new, script = save_variant(
        project.root,
        project.experiment,
        name="supernemo-four-001",
        changes={"iterations": 4, "formal_minutes": 6},
    )
    monkeypatch.chdir(tmp_path)
    validate_launcher(new, script)
    review = demo.review(new, script)
    assert str(new) in review and str(script) in review
    assert project.experiment.read_bytes() == before
    assert SuperNemoExperiment.model_validate_json(new.read_text()).iterations == 4
    with pytest.raises(ValueError, match="new variant name"):
        save_variant(
            project.root, project.experiment, name="supernemo-four-001", changes={}
        )


def test_changed_index_refuses_completed_result_reuse(project, monkeypatch):
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
    with (settings.data_dir / "event_indexes/0nubb_event_index.npz").open("ab") as f:
        f.write(b"changed")
    with pytest.raises(ValueError, match="index/report changed"):
        demo.run_demo(project.experiment, project.script)
    assert json.loads(receipt.read_text()) == result


def test_missing_key_refuses_before_logs_or_workspace(project, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="Missing exported keys: OPENAI_API_KEY"):
        demo.run_demo(project.experiment, project.script)
    assert not project.settings.workspace.exists()
    assert not project.settings.workspace.with_suffix(".console.log").exists()


def test_source_alias_refused(project):
    with pytest.raises(ValueError, match="separate"):
        create_project(ROOT / "illegal-project", ROOT, project.settings.data_dir)
    with pytest.raises(ValueError, match="separate"):
        create_project(
            project.settings.data_dir / "illegal-project",
            ROOT,
            project.settings.data_dir,
        )


def test_original_raw_parent_is_protected_behind_prepared_links(project):
    raw_parent = (project.settings.data_dir / "data_0nubb_merged.h5").resolve().parent
    with pytest.raises(ValueError, match="separate from original raw"):
        create_project(raw_parent / "illegal-project", ROOT, project.settings.data_dir)
    changed = SuperNemoExperiment.model_validate(
        {**project.settings.model_dump(), "workspace": raw_parent / "illegal-run"}
    )
    with pytest.raises(ValueError, match="separate from original raw"):
        runner.build_command(changed)
    assert not (raw_parent / "illegal-project").exists()
    assert not (raw_parent / "illegal-run").exists()


@pytest.mark.parametrize("completed", [False, True])
def test_real_notebook_cells_with_fixture_data_and_cached_result(
    project, tmp_path, completed
):
    import nbformat
    from jupyter_client import KernelManager
    from nbclient import NotebookClient

    notebook = nbformat.read(
        project.root / "notebooks/supernemo_tutorial.ipynb", as_version=4
    )
    for cell in notebook.cells:
        if cell.cell_type == "code" and not completed:
            cell.source = cell.source.replace(
                "RUN_NATIVE_PREVIEW = True", "RUN_NATIVE_PREVIEW = False"
            ).replace("RUN_QUICK_DEMO = True", "RUN_QUICK_DEMO = False")
    notebook.cells.insert(
        0,
        nbformat.v4.new_code_cell(
            f"import os,sys\nos.chdir({str(ROOT)!r})\nfrom pathlib import Path\n"
            "from tutorials.supplementary.supernemo import data,prepare\n"
            f"data.SOURCE_MANIFEST=prepare.SOURCE_MANIFEST=Path({str(project.authority)!r})\n"
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
    env.pop("OPENAI_API_KEY", None)
    if completed:
        project.settings.workspace.mkdir()
        result = {
            "input_sha256": demo.input_digest(project.experiment, project.script),
            "exit_code": 0,
            "workspace": str(project.settings.workspace),
        }
        receipt = project.settings.workspace.with_suffix(".notebook-run.json")
        receipt.write_text(json.dumps(result))
        before = receipt.read_bytes()
    client = NotebookClient(
        notebook,
        km=manager,
        timeout=120,
        resources={"metadata": {"path": str(tmp_path)}},
    )
    client.execute(env=env)
    if completed:
        client.execute(env=env)
        assert receipt.read_bytes() == before
    output = str([c.get("outputs", []) for c in notebook.cells])
    assert "supernemo-demo.json" in output
    assert (
        "Reusing recorded result without API/GPU work"
        if completed
        else "Live search disabled"
    ) in output


def test_no_health_progress_keeps_failed_scores_and_refuses_empty_chart(project):
    from tests.tutorials.test_progress_demo import write_record
    from tutorials.shared.progress import read_progress

    output = write_record(
        project.settings.workspace, score=0.6, status="failed_mode_collapse"
    )
    payload = json.loads(output.read_text())
    for record in payload["all_records"]:
        record["health_gate_results"] = []
        record["denoising_score"] = 0.6
        record["metric_result"]["metric_id"] = "energy_matched_roc_auc"
    output.write_text(json.dumps(payload))
    point = read_progress(project.settings.workspace, health_policy="none")[0]
    assert point.score == 0.6 and point.validity == "fail"
    figure = demo.plot_results(project.experiment, project.root / "plots/failed")
    assert list(figure.axes[0].collections[0].get_facecolors()[0]) == [1, 1, 1, 1]
    for record in payload["all_records"]:
        record["metric_result"] = None
        record["denoising_score"] = None
    output.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="No measured Formal score"):
        demo.plot_results(project.experiment, project.root / "plots/missing")
