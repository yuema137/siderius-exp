"""Witness false cache hits without any native training or provider request."""

import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from tests.tutorials.test_progress_demo import write_record
from tutorials.paper import quick_demo
from tutorials.paper.progress import read_progress
from tutorials.paper.result_identity import read_settings
from tutorials.paper.runner import ROOT


@pytest.fixture(params=["tess", "tidmad", "project8", "ligo"])
def demo(tmp_path, monkeypatch, request):
    """Real initialized files, actual run_demo decisions, fake effectful boundaries."""
    task = request.param
    project = tmp_path / "editable project with spaces"
    if task in ("project8", "ligo"):
        from tutorials.paper.prepared import runner
        from tutorials.paper.prepared.project import create_project

        create_project(project, ROOT, task)
        # Local task copy only: no external arrays/download needed by this cache test.
        shutil.copytree(
            ROOT / f"tasks/phyts_{task}", project / f"tasks/{task}-demo-001"
        )
        composition = project / f"tasks/{task}-demo-001/compositions/regression.yaml"
        if not composition.exists():
            shutil.copyfile(
                composition.with_name("dual_representation.yaml"), composition
            )
    elif task == "tidmad":
        from tutorials.paper.tidmad import runner
        from tutorials.paper.tidmad.project import create_project

        create_project(project, ROOT)
    else:
        from tutorials.paper import runner
        from tutorials.paper.project import create_project

        create_project(project, ROOT)
    files = quick_demo.prepare_demo(
        project, task, name="quick", settings={"iterations": 3}
    )
    settings = read_settings(files.experiment, task)
    workflow, treatment = (
        runner.workflow_files(settings)
        if task in ("project8", "ligo")
        else runner.workflow_files()
    )
    # Isolate mutations of actual fixed workflow/treatment files from tracked source.
    workflow_copy, treatment_copy = (
        tmp_path / "workflow.json",
        tmp_path / "treatment.yaml",
    )
    shutil.copyfile(workflow, workflow_copy)
    shutil.copyfile(treatment, treatment_copy)
    monkeypatch.setattr(
        runner, "workflow_files", lambda *a: (workflow_copy, treatment_copy)
    )
    calls = {"launch": 0, "preflight": 0, "inspect": 0}

    def preflight(*args, **kwargs):
        calls["preflight"] += 1

    def inspect(*args, **kwargs):
        calls["inspect"] += 1

    state = SimpleNamespace(exit_code=0, during_wait=None)

    class Process:
        def __init__(self, argv, **kwargs):
            assert argv == ["bash", str(files.script), "--launch"]
            calls["launch"] += 1
            files.workspace.mkdir()
            write_record(files.workspace, score=-0.4, status="failed_mode_collapse")

        def wait(self, *, timeout):
            if state.during_wait:
                state.during_wait()
            return state.exit_code

    monkeypatch.setattr("tutorials.paper.preflight.require_ready", preflight)
    monkeypatch.setattr(runner, "inspect", inspect)
    monkeypatch.setattr(
        "tutorials.paper.launch_review.launch_review", lambda *a, **k: "ready"
    )
    monkeypatch.setattr(
        quick_demo,
        "subprocess",
        SimpleNamespace(
            Popen=Process,
            STDOUT=subprocess.STDOUT,
            SubprocessError=subprocess.SubprocessError,
            TimeoutExpired=subprocess.TimeoutExpired,
        ),
    )
    return SimpleNamespace(
        files=files,
        settings=settings,
        project=project,
        task=task,
        calls=calls,
        state=state,
        workflow=workflow_copy,
        treatment=treatment_copy,
    )


def complete(demo):
    result = quick_demo.run_demo(demo.files)
    assert demo.calls == {"launch": 1, "preflight": 1, "inspect": 1}
    return result


def test_unchanged_run_reuses_without_launch_checks_even_with_bytecode_and_no_keys(
    demo, monkeypatch
):
    first = complete(demo)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    task_dir = demo.settings.composition.parent.parent
    cache = task_dir / "__pycache__"
    cache.mkdir(exist_ok=True)
    (cache / "generated.cpython-312.pyc").write_bytes(b"cache only")
    # The cache does not promise to rehash raw arrays on plot/reuse.
    demo.settings.data_dir.mkdir(parents=True, exist_ok=True)
    (demo.settings.data_dir / "unread-raw-bytes").write_bytes(b"raw data")
    assert quick_demo.run_demo(demo.files) == first
    assert demo.calls == {"launch": 1, "preflight": 1, "inspect": 1}


@pytest.mark.parametrize(
    "changed", ["experiment", "routing", "task", "script", "workflow", "treatment"]
)
def test_changed_input_refuses_reuse_without_overwriting_evidence(demo, changed):
    complete(demo)
    receipt = demo.files.completion.read_bytes()
    paths = {
        "experiment": demo.files.experiment,
        "routing": demo.settings.llm_config,
        "task": demo.settings.composition,
        "script": demo.files.script,
        "workflow": demo.workflow,
        "treatment": demo.treatment,
    }
    path = paths[changed]
    if changed == "experiment":
        config = json.loads(path.read_text())
        config["iterations"] = 4
        path.write_text(json.dumps(config))
    else:
        path.write_text(path.read_text() + "\n")
    with pytest.raises(
        ValueError, match="Saved inputs changed.*Nothing was relaunched"
    ):
        quick_demo.run_demo(demo.files)
    assert demo.calls["launch"] == 1 and demo.calls["preflight"] == 1
    assert demo.files.completion.read_bytes() == receipt
    assert read_progress(demo.files.workspace)[0].score == -0.4


@pytest.mark.parametrize("mutation", ["add", "delete", "edit"])
def test_task_runtime_tree_changes_refuse_reuse(demo, mutation):
    task_dir = demo.settings.composition.parent.parent
    path = task_dir / "local_runtime.py"
    path.write_text("implementation = 1\n")
    complete(demo)
    if mutation == "add":
        (task_dir / "new_plugin.py").write_text("implementation = 2\n")
    elif mutation == "delete":
        path.unlink()
    else:
        path.write_text("implementation = 2\n")
    with pytest.raises(ValueError, match="Saved inputs changed"):
        quick_demo.run_demo(demo.files)
    assert demo.calls["launch"] == 1


def test_selected_literature_and_prepared_shared_code_are_bound(demo):
    complete(demo)
    if demo.task in ("project8", "ligo"):
        path = demo.settings.literature_config
    elif demo.task == "tidmad":
        path = (
            demo.settings.composition.parent.parent
            / "framework_configs/lit_review.yaml"
        )
    else:
        return  # TESS explicitly disables literature review.
    original = path.read_bytes()
    path.write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="Saved inputs changed"):
        quick_demo.run_demo(demo.files)
    path.write_bytes(original)
    if demo.task in ("project8", "ligo"):
        shared = demo.project / "tasks/shared/prepared_regression.py"
        shared.write_text(shared.read_text() + "\n")
        with pytest.raises(ValueError, match="Saved inputs changed"):
            quick_demo.run_demo(demo.files)
    assert demo.calls["launch"] == 1


def test_missing_workspace_never_becomes_a_cache_hit_or_a_new_launch(demo):
    complete(demo)
    receipt = demo.files.completion.read_bytes()
    shutil.rmtree(demo.files.workspace)
    with pytest.raises(ValueError, match="Completed workspace is missing"):
        quick_demo.run_demo(demo.files)
    assert demo.files.completion.read_bytes() == receipt
    assert not demo.files.workspace.exists()
    assert demo.calls["launch"] == 1


def test_carrier_cannot_relabel_another_experiments_workspace(demo):
    complete(demo)
    forged = demo.files.model_copy(update={"workspace": demo.project / "runs/other"})
    with pytest.raises(
        ValueError, match="saved experiment and demo workspace disagree"
    ):
        quick_demo.run_demo(forged)
    payload = json.loads(demo.files.completion.read_text())
    payload["workspace"] = str(forged.workspace)
    demo.files.completion.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="Completion belongs to a different workspace"):
        quick_demo.run_demo(demo.files)
    assert demo.calls["launch"] == 1


@pytest.mark.parametrize(
    "receipt",
    [
        '{"experiment_sha256": "old", "exit_code": 0}',
        '{"version": "paper-demo-completion-v2"}',
        "not json",
    ],
)
def test_old_or_invalid_receipt_keeps_records_and_gives_plot_only_route(demo, receipt):
    demo.files.completion.write_text(receipt)
    demo.files.workspace.mkdir()
    with pytest.raises(
        ValueError, match="Old or invalid completion.*PLOT_WORKSPACE.*PLOT_EXPERIMENT"
    ):
        quick_demo.run_demo(demo.files)
    assert demo.calls == {"launch": 0, "preflight": 0, "inspect": 0}
    assert demo.files.completion.read_text() == receipt


def test_nonzero_completion_preserves_failed_outcome_and_scored_records(demo, capsys):
    demo.state.exit_code = 7
    result = complete(demo)
    assert result["exit_code"] == 7
    assert quick_demo.run_demo(demo.files)["exit_code"] == 7
    assert "Recorded script exit code: 7" in capsys.readouterr().out
    points = read_progress(demo.files.workspace)
    assert points[0].score == -0.4 and points[0].validity == "fail"
    assert demo.calls["launch"] == 1


def test_edit_during_preflight_stops_before_saved_script_launch(demo, monkeypatch):
    def edit(*args, **kwargs):
        demo.settings.llm_config.write_text(demo.settings.llm_config.read_text() + "\n")

    monkeypatch.setattr("tutorials.paper.preflight.require_ready", edit)
    with pytest.raises(ValueError, match="Inputs changed during launch checks"):
        quick_demo.run_demo(demo.files)
    assert demo.calls["launch"] == 0
    assert not demo.files.completion.exists() and not demo.files.log.exists()


def test_midrun_edit_marks_receipt_unusable_even_if_inputs_later_restored(demo):
    original = demo.settings.llm_config.read_bytes()
    demo.state.during_wait = lambda: demo.settings.llm_config.write_bytes(
        original + b"\n"
    )
    result = complete(demo)
    assert result["inputs_unchanged"] is False
    demo.settings.llm_config.write_bytes(original)
    with pytest.raises(ValueError, match="Inputs changed during the recorded run"):
        quick_demo.run_demo(demo.files)
    assert demo.calls["launch"] == 1


def test_source_revision_or_tracked_edits_cannot_silently_change(demo, monkeypatch):
    complete(demo)
    monkeypatch.setattr(
        "tutorials.paper.result_identity._source_identity",
        lambda _: ("different-revision", "different-diff"),
    )
    with pytest.raises(ValueError, match="Saved inputs changed"):
        quick_demo.run_demo(demo.files)
    assert demo.calls["launch"] == 1


def test_missing_routing_refuses_cache_hit_without_launch(demo):
    complete(demo)
    demo.settings.llm_config.unlink()
    with pytest.raises(ValueError, match="Cannot verify.*PLOT_WORKSPACE"):
        quick_demo.run_demo(demo.files)
    assert demo.calls["launch"] == 1


@pytest.mark.parametrize("mutation", ["deleted", "malformed"])
def test_unreadable_saved_experiment_preserves_results_and_explains_recovery(
    demo, mutation
):
    complete(demo)
    receipt = demo.files.completion.read_bytes()
    if mutation == "deleted":
        demo.files.experiment.unlink()
    else:
        demo.files.experiment.write_text("not valid JSON")
    with pytest.raises(
        ValueError,
        match="Cannot read the saved experiment.*Restore.*PLOT_EXPERIMENT.*Nothing was relaunched.*new DEMO_NAME",
    ):
        quick_demo.run_demo(demo.files)
    assert demo.calls == {"launch": 1, "preflight": 1, "inspect": 1}
    assert demo.files.completion.read_bytes() == receipt
    assert read_progress(demo.files.workspace)[0].score == -0.4
    if mutation == "deleted":
        assert not demo.files.experiment.exists()
    else:
        assert demo.files.experiment.read_text() == "not valid JSON"
