"""Saved-demo lessons must preserve the learner's selected inputs and run identity."""

import json
import shlex
from types import SimpleNamespace

import pytest

from tutorials.paper import quick_demo
from tutorials.paper.result_identity import read_settings
from tutorials.paper.runner import ROOT
from tutorials.paper.saved_demo import load_demo, save_variant


@pytest.fixture(params=["tess", "tidmad"])
def saved(tmp_path, request):
    task = request.param
    if task == "tidmad":
        from tutorials.paper.tidmad.project import create_project
        from tutorials.paper.tidmad.runner import build_command
    else:
        from tutorials.paper.project import create_project
        from tutorials.paper.runner import build_command
    project = tmp_path / "editable project with spaces"
    create_project(project, tmp_path / "infra")
    files = quick_demo.prepare_demo(
        project,
        task,
        name="original",
        settings={
            "iterations": 3,
            "epochs": 5,
            "trial_minutes": 3,
            "formal_minutes": 7,
            "trial_train_fraction": 0.03,
            "trial_val_fraction": 0.07,
            "formal_train_fraction": 0.2,
            "formal_val_fraction": 0.4,
        },
    )
    settings = read_settings(files.experiment, task)
    # A saved routing change must survive even though the initializer still differs.
    routing = project / "llm/selected.json"
    routing.write_bytes(settings.llm_config.read_bytes())
    settings = type(settings).model_validate(
        settings.model_dump() | {"llm_config": routing}
    )
    files.experiment.write_text(settings.model_dump_json(indent=2))
    original = {
        p: p.read_bytes() for p in (project / "tasks").rglob("*") if p.is_file()
    }
    original[files.experiment] = files.experiment.read_bytes()
    original[files.script] = files.script.read_bytes()
    return SimpleNamespace(
        task=task,
        project=project,
        files=files,
        settings=settings,
        original=original,
        build_command=build_command,
    )


def test_clone_reads_saved_values_and_reopens_without_recreating_task(saved):
    new = save_variant(
        saved.project, saved.files, name="four", changes={"iterations": 4}
    )
    actual = read_settings(new.experiment, saved.task)
    old = saved.settings.model_dump()
    expected = old | {
        "iterations": 4,
        "run_name": f"{saved.task}_four",
        "workspace": new.workspace,
    }
    assert actual.model_dump() == expected
    assert load_demo(saved.project, saved.task, name="four") == new
    assert all(p.read_bytes() == data for p, data in saved.original.items())
    assert not new.workspace.exists()
    command = saved.build_command(actual)
    assert command[command.index("--num_iterations") + 1] == "4"
    assert command[command.index("--task_composition") + 1] == str(
        saved.settings.composition
    )
    assert command[command.index("--llm_config") + 1] == str(saved.settings.llm_config)
    assert command[command.index("--formal_portion") + 1] == "0.2"
    assert command[command.index("--max_epochs") + 1] == "5"
    if saved.task == "tidmad":
        assert actual.protocol == "file-holdout"
        assert actual.composition.name == "file_holdout.yaml"
    assert shlex.split(
        next(
            s
            for s in new.script.read_text().splitlines()
            if s.startswith("EXPERIMENT=")
        ).split("=", 1)[1]
    ) == [str(new.experiment)]


@pytest.mark.parametrize(
    "destination", ["json", "script", "workspace", "log", "completion"]
)
def test_existing_destination_refusal_has_no_writes(saved, destination):
    name = f"{saved.task}_occupied"
    target = {
        "json": saved.project / f"experiments/{name}.json",
        "script": saved.project / f"scripts/run-{name}.sh",
        "workspace": saved.project / f"runs/{name}",
        "log": saved.project / f"runs/{name}.console.log",
        "completion": saved.project / f"runs/{name}.notebook-run.json",
    }[destination]
    target.write_text("previous evidence")
    before = {p: p.read_bytes() for p in saved.project.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="fresh demo name"):
        save_variant(
            saved.project, saved.files, name="occupied", changes={"iterations": 4}
        )
    assert before == {
        p: p.read_bytes() for p in saved.project.rglob("*") if p.is_file()
    }


def test_invalid_changes_refuse_before_writing(saved):
    with pytest.raises(ValueError):
        save_variant(saved.project, saved.files, name="bad", changes={"iterations": 0})
    with pytest.raises(ValueError, match="fresh run identity"):
        save_variant(
            saved.project,
            saved.files,
            name="bad",
            changes={"workspace": saved.files.workspace},
        )
    assert not (saved.project / f"experiments/{saved.task}_bad.json").exists()
    assert all(p.read_bytes() == data for p, data in saved.original.items())


def test_actual_notebook_cells_save_select_review_and_reopen(
    saved, monkeypatch, capsys
):
    prefix = "01" if saved.task == "tess" else "02"
    notebook = json.loads(
        (
            ROOT / f"tutorials/paper/notebooks/{prefix}_{saved.task}_tutorial.ipynb"
        ).read_text()
    )
    codes = [
        "".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code"
    ]
    select = next(
        s
        for s in codes
        if s.startswith("from tutorials.paper.result_identity import read_settings")
    )
    save = next(s for s in codes if s.startswith("SAVE_CHANGED_DEMO = False"))
    # Presence-only review fixtures; no raw data is loaded and no effect is authorized.
    data = saved.settings.data_dir
    data.mkdir(parents=True, exist_ok=True)
    if saved.task == "tess":
        names = ["tess_rotation_train.npz", "tess_rotation_val.npz"]
    else:
        names = [
            f"abra_{role}_{i:04d}.h5"
            for role in ("training", "validation")
            for i in range(4)
        ]
    for name in names:
        (data / name).touch()
    monkeypatch.setattr(
        quick_demo, "run_demo", lambda *_: pytest.fail("lesson launched a second run")
    )
    displays = []
    monkeypatch.setattr(
        "IPython.display.display", lambda value: displays.append(value.data)
    )
    ns = {"PROJECT": saved.project, "demo": saved.files}
    before = set(saved.project.rglob("*"))
    exec(compile(select, "notebook-selection", "exec"), ns)  # noqa: S102 -- repository-owned teaching cell
    exec(compile(save, "notebook-save-disabled", "exec"), ns)  # noqa: S102
    assert set(saved.project.rglob("*")) == before
    assert ns["selected_demo"] == saved.files
    enabled = save.replace("SAVE_CHANGED_DEMO = False", "SAVE_CHANGED_DEMO = True")
    exec(compile(enabled, "notebook-save", "exec"), ns)  # noqa: S102
    chosen = ns["selected_demo"]
    assert ns["selected_settings"].iterations == 4
    assert chosen.experiment.name == f"{saved.task}_quick-demo-four-001.json"
    assert ns["SELECTED_PLOT_OUTPUT"] == saved.project / "plots" / chosen.workspace.name
    assert str(chosen.experiment) in displays[-1]
    assert shlex.join(["bash", str(chosen.script)]) in displays[-1]
    assert "--launch" in displays[-1]
    assert str(chosen.workspace) in capsys.readouterr().out
    # Reopening skips prepare_demo and uses saved JSON even if initializer is gone.
    (saved.project / f"experiments/{saved.task}-experiment.json").unlink()
    reopened = select.replace(
        "SELECTED_DEMO_NAME = None", 'SELECTED_DEMO_NAME = "quick-demo-four-001"'
    )
    # A fresh kernel has no Quick A imports or prior lesson globals.
    fresh = {"PROJECT": saved.project}
    exec(compile(reopened, "notebook-reopen", "exec"), fresh)  # noqa: S102
    exec(compile(save, "notebook-review-reopened", "exec"), fresh)  # noqa: S102
    assert fresh["selected_demo"] == chosen
    assert str(chosen.experiment) in displays[-1]
    assert shlex.join(["bash", str(chosen.script)]) in displays[-1]
    assert not chosen.workspace.exists()
