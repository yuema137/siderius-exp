"""The notebook must never advertise a different experiment's launch command."""

import json
from pathlib import Path

import pytest

from tutorials.paper.launch_review import launch_review
from tutorials.paper.project import create_project as create_tess
from tutorials.paper.tidmad.project import create_project as create_tidmad


@pytest.fixture(params=["tess", "tidmad"])
def review_project(tmp_path, request):
    task = request.param
    project = tmp_path / "external project with spaces"
    (create_tess if task == "tess" else create_tidmad)(
        project, tmp_path / "installed infra"
    )
    config = project / "experiments" / f"{task}-experiment.json"
    script = project / "scripts" / f"run-{task}.sh"
    return task, config, script


def stage_presence_only(config, task):
    data = Path(json.loads(config.read_text())["data_dir"])
    data.mkdir(exist_ok=True)
    names = (
        [f"tess_rotation_{split}.npz" for split in ("train", "val")]
        if task == "tess"
        else [
            f"abra_{family}_{i:04d}.h5"
            for family in ("training", "validation")
            for i in range(4)
        ]
    )
    for name in names:
        (data / name).touch()


def test_review_rereads_edits_and_quotes_actual_script(review_project):
    task, config, script = review_project
    stage_presence_only(config, task)
    first = launch_review(config, script, task=task)
    data = json.loads(config.read_text())
    data["epochs"] = 7
    data["trial_vram_gib"] = 3
    config.write_text(json.dumps(data))
    second = launch_review(config, script, task=task)
    assert "| `epochs` | `1` |" in first
    assert "| `epochs` | `7` |" in second
    assert "Effective Trial budget: 3.0 GiB" in second
    assert f"bash '{script}' --launch" in second
    assert str(config) in second
    assert not Path(data["workspace"]).exists()


def test_no_command_for_missing_data_or_existing_workspace(review_project):
    task, config, script = review_project
    assert "--launch" not in launch_review(config, script, task=task)
    stage_presence_only(config, task)
    Path(json.loads(config.read_text())["workspace"]).mkdir()
    report = launch_review(config, script, task=task)
    assert "STOP" in report
    assert "--launch" not in report


def test_wrong_experiment_binding_refuses_without_executing_script(review_project):
    task, config, script = review_project
    script.write_text(
        script.read_text().replace(str(config), str(config.with_name("other.json")))
    )
    with pytest.raises(ValueError, match="different JSON"):
        launch_review(config, script, task=task)


def test_final_test_script_cannot_be_mistaken_for_search(review_project):
    task, config, script = review_project
    original = (
        "tutorials.paper.runner" if task == "tess" else "tutorials.paper.tidmad.runner"
    )
    script.write_text(
        script.read_text().replace(original, "tutorials.paper.tidmad.final_test")
    )
    with pytest.raises(ValueError, match="search launcher"):
        launch_review(config, script, task=task)
