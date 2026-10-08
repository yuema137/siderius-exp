"""Execute current notebook input cells without downloads, kernels or launches."""

import ast
import json
import re
import shlex
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS = ROOT / "tutorials/paper/notebooks"
DATA_CELLS = {
    "tess": ("01_tess_tutorial.ipynb", 16, "preparation"),
    "tidmad": ("02_tidmad_tutorial.ipynb", 15, "command"),
}


def source(name, index):
    return "".join(json.loads((NOTEBOOKS / name).read_text())["cells"][index]["source"])


def run_data_cell(tmp_path, task, *, entry="prepared", existing=None):
    name, index, command_name = DATA_CELLS[task]
    tree = ast.parse(source(name, index))
    # Model the reader editing only these two declared input values.
    tree.body = [
        statement
        for statement in tree.body
        if not (
            isinstance(statement, ast.Assign)
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id in {"DATA_ENTRY", "EXISTING_SOURCE"}
        )
    ]
    namespace = {
        "Path": Path,
        "sys": sys,
        "shlex": shlex,
        "EXP": tmp_path / "exp",
        "INFRA": tmp_path / "infra",
        "PROJECT": tmp_path / "project",
        "base": SimpleNamespace(data_dir=tmp_path / "project/data"),
        "DATA_ENTRY": entry,
        "EXISTING_SOURCE": existing,
    }
    # Execute only the reviewed, tracked cell; no user-supplied program is loaded.
    exec(compile(tree, name, "exec"), namespace)  # noqa: S102
    return namespace[command_name], namespace


@pytest.mark.parametrize("task", DATA_CELLS)
def test_prepared_default_prints_saved_location_without_preparation(
    tmp_path, task, capsys
):
    name, index, _ = DATA_CELLS[task]
    inputs = {}
    for statement in ast.parse(source(name, index)).body:
        if (
            isinstance(statement, ast.Assign)
            and isinstance(statement.targets[0], ast.Name)
            and statement.targets[0].id in {"DATA_ENTRY", "EXISTING_SOURCE"}
        ):
            inputs[statement.targets[0].id] = ast.literal_eval(statement.value)
    assert inputs == {"DATA_ENTRY": "prepared", "EXISTING_SOURCE": None}
    command, _ = run_data_cell(tmp_path, task)
    output = capsys.readouterr().out
    assert command is None
    assert str(tmp_path / "project/data") in output
    assert "Run once" not in output
    assert "No data preparation or validation was performed." in output
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("task", DATA_CELLS)
@pytest.mark.parametrize("as_string", [False, True])
def test_explicit_source_command_matches_actual_data_entry_parser(
    tmp_path, task, as_string, monkeypatch, capsys
):
    from tutorials.paper import data_entry

    existing = tmp_path / "user data"
    existing.mkdir()
    command, namespace = run_data_cell(
        tmp_path,
        task,
        entry="existing",
        existing=str(existing) if as_string else existing,
    )
    output = capsys.readouterr().out
    assert shlex.join(command) in output
    assert command[:4] == [
        str(namespace["EXP"] / ".venv/bin/python"),
        "-B",
        "-m",
        "tutorials.paper.data_entry",
    ]
    observed = []
    monkeypatch.setattr(
        data_entry,
        f"use_existing_{task}",
        lambda project, source: observed.append((project, source)),
    )
    monkeypatch.setattr(sys, "argv", ["data_entry", *command[4:]])
    data_entry.main()
    assert observed == [(namespace["PROJECT"], existing)]
    assert sorted(tmp_path.iterdir()) == [existing]
    assert list(existing.iterdir()) == []


@pytest.mark.parametrize("task", DATA_CELLS)
@pytest.mark.parametrize("bad", [None, True, 12, "relative/data"])
def test_existing_source_requires_explicit_absolute_path(tmp_path, task, bad):
    with pytest.raises(ValueError, match="absolute"):
        run_data_cell(tmp_path, task, entry="existing", existing=bad)


@pytest.mark.parametrize("task", DATA_CELLS)
def test_existing_source_refuses_missing_directory_and_checkout_alias(tmp_path, task):
    with pytest.raises(ValueError, match="existing data directory"):
        run_data_cell(tmp_path, task, entry="existing", existing=tmp_path / "missing")
    checkout = tmp_path / "infra"
    checkout.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(checkout, target_is_directory=True)
    for path in (checkout, alias, tmp_path):
        with pytest.raises(ValueError, match="separate"):
            run_data_cell(tmp_path, task, entry="existing", existing=path)


@pytest.mark.parametrize("task", DATA_CELLS)
def test_download_branch_only_prints_explicit_command(tmp_path, task, capsys):
    command, namespace = run_data_cell(tmp_path, task, entry="download")
    assert shlex.join(command) in capsys.readouterr().out
    if task == "tess":
        assert command[3] == "tutorials.paper.prepare_tess"
        assert command[-1] == str(namespace["PROJECT"] / "data/tess-data")
    else:
        assert command[1] == "/absolute/path/to/TIDMAD/download_data.py"
        assert command[-2:] == ["--science_files", "0"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "name", ["03_project8_tutorial.ipynb", "04_ligo_tutorial.ipynb"]
)
def test_quick_settings_do_not_force_recorded_gpu_name(tmp_path, name):
    tree = ast.parse(source(name, 5))
    statement = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "QUICK_SETTINGS"
    )
    namespace = {"PROJECT": tmp_path, "DATA_NAME": "demo-001"}
    # Exercise the tracked literal input assignment without running Quick A.
    exec(  # noqa: S102
        compile(ast.Module(body=[statement], type_ignores=[]), name, "exec"), namespace
    )
    assert namespace["QUICK_SETTINGS"]["gpu"] is None
    assert namespace["QUICK_SETTINGS"]["composition"].is_absolute()


def test_touched_current_tutorial_links_do_not_use_retired_main_branch():
    instructions = [
        ROOT / "tutorials/paper/README.md",
        ROOT / "tutorials/paper/tidmad/README.md",
        ROOT / "tutorials/paper/prepared/README.md",
        ROOT / "tutorials/supplementary/pet/README.md",
    ]
    texts = [(str(path), path.read_text()) for path in instructions]
    for path in NOTEBOOKS.glob("*.ipynb"):
        notebook = json.loads(path.read_text())
        texts.extend(
            (f"{path}:cell{index}", "".join(cell["source"]))
            for index, cell in enumerate(notebook["cells"])
        )
    retired = re.compile(
        r"https://github\.com/yuema137/(?:siderius-exp|SIDERIUS)/(?:tree|blob)/main(?:[/#?)]|$)"
    )
    for location, text in texts:
        assert retired.search(text) is None, location
