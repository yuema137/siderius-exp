"""Pet propagation, split isolation and external launcher regression checks."""

import hashlib
import json
import subprocess

import pytest

from tutorials.shared.runtime import ROOT
from tutorials.supplementary.pet.data import inspect_data, read_splits, resplit_task
from tutorials.supplementary.pet.project import create_project
from tutorials.supplementary.pet.runner import build_command
from tutorials.supplementary.pet.settings import PetExperiment


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "new user project"
    experiment = create_project(path, tmp_path / "infra", tmp_path / "images")
    return path, experiment


def test_saved_edits_reach_native_arguments_and_remain_external(project):
    """Catch a launcher silently reading templates instead of the edited JSON."""
    path, experiment = project
    data = json.loads(experiment.read_text())
    data.update(
        iterations=4,
        epochs=7,
        trial_train_fraction=0.25,
        trial_val_fraction=0.75,
        formal_train_fraction=0.9,
        formal_val_fraction=0.8,
        trial_minutes=3,
        formal_minutes=6,
        vram_gib=9,
    )
    experiment.write_text(json.dumps(data))
    command = build_command(PetExperiment.model_validate_json(experiment.read_text()))
    expected = {
        "--num_iterations": "4",
        "--trial_max_epochs": "7",
        "--formal_max_epochs": "7",
        "--trial_portion": "0.25",
        "--eval_portion": "0.75",
        "--formal_portion": "0.9",
        "--formal_eval_portion": "0.8",
        "--trial_time_budget_minutes": "3.0",
        "--formal_time_budget_minutes": "6.0",
        "--trial_vram_budget_gb": "9.0",
        "--train_portion": "1.0",
        "--formal_train_portion": "1.0",
    }
    for flag, value in expected.items():
        assert command.count(flag) == 1
        assert command[command.index(flag) + 1] == value
    assert command[command.index("--task_composition") + 1] == str(
        path / "tasks/pet/compositions/bounded_qualification.yaml"
    )
    assert command[command.index("--llm_config") + 1] == str(path / "llm/agents.json")
    copied_notebook = json.loads((path / "notebooks/pet_tutorial.ipynb").read_text())
    assert all(
        not cell.get("outputs") and cell.get("execution_count") is None
        for cell in copied_notebook["cells"]
        if cell["cell_type"] == "code"
    )
    script = path / "scripts/run-pet.sh"
    subprocess.run(["bash", "-n", str(script)], check=True)
    assert f"EXPERIMENT='{experiment}'" in script.read_text()
    assert '--experiment "$EXPERIMENT"' in script.read_text()


def test_resplit_changes_only_new_training_validation_identity(project):
    """Catch leakage into final or an in-place change to historical task science."""
    path, experiment = project
    settings = PetExperiment.model_validate_json(experiment.read_text())
    task = settings.composition.parent.parent
    before = {
        str(p.relative_to(task)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in task.rglob("*")
        if p.is_file()
    }
    changed = resplit_task(
        settings.composition,
        path / "tasks/pet-new-split",
        validation_per_class=3,
        seed=2026,
    )
    old, new = read_splits(settings.composition), read_splits(changed)
    assert len(new["train"]) == 333
    assert len(new["validation"]) == 111
    assert {r.image_id for r in (*new["train"], *new["validation"])} == {
        r.image_id for r in (*old["train"], *old["validation"])
    }
    assert new["final"] == old["final"]
    assert {
        str(p.relative_to(task)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in task.rglob("*")
        if p.is_file()
    } == before
    from workflows.task_composition import compose_run_task_bindings

    assert (
        compose_run_task_bindings(str(settings.composition)).semantic_fingerprint
        != compose_run_task_bindings(str(changed)).semantic_fingerprint
    )
    with pytest.raises(ValueError, match="never overwrites"):
        resplit_task(
            settings.composition, changed.parent.parent, validation_per_class=2, seed=3
        )


def test_missing_image_and_overlapping_split_refused(project, tmp_path):
    """Catch launch accepting incomplete local data or using validation for training."""
    _, experiment = project
    settings = PetExperiment.model_validate_json(experiment.read_text())
    with pytest.raises(ValueError, match="Missing image"):
        inspect_data(settings.composition, tmp_path / "missing")
    task = settings.composition.parent.parent
    train = task / "data/manifests/gate2_train.csv"
    validation = task / "data/manifests/gate2_validation.csv"
    validation.write_text(train.read_text().replace(",train", ",validation"))
    with pytest.raises(ValueError, match="overlap"):
        read_splits(settings.composition)


def test_no_overwrite_or_in_repo_output(project, tmp_path):
    """Catch destructive launch/output aliases; schema field validation alone cannot."""
    path, experiment = project
    with pytest.raises(ValueError, match="never overwritten"):
        create_project(path, tmp_path / "infra", tmp_path / "images")
    settings = PetExperiment.model_validate_json(experiment.read_text())
    for workspace in (ROOT / "bad-run", settings.data_dir / "bad-run"):
        with pytest.raises(ValueError):
            build_command(
                PetExperiment.model_validate(
                    {**settings.model_dump(), "workspace": workspace}
                )
            )
    settings.workspace.mkdir()
    with pytest.raises(ValueError, match="already exists"):
        build_command(settings)


def test_completion_reuse_binds_task_and_routing_inputs(project):
    """Catch a rerun silently reusing scores after changing science or LLM routing."""
    from tutorials.supplementary.pet.demo import input_digest, run_demo

    path, experiment = project
    script = path / "scripts/run-pet.sh"
    settings = PetExperiment.model_validate_json(experiment.read_text())
    settings.workspace.mkdir()
    completion = settings.workspace.with_suffix(".notebook-run.json")
    completion.write_text(
        json.dumps({"input_sha256": input_digest(experiment, script), "exit_code": 0})
    )
    assert run_demo(experiment, script)["exit_code"] == 0
    config = settings.composition.parent.parent / "declared/task_config.yaml"
    config.write_text(config.read_text() + "\n# A deliberate task edit\n")
    with pytest.raises(ValueError, match="Inputs changed"):
        run_demo(experiment, script)


def test_timeout_stops_detached_worker(project, monkeypatch):
    """Catch notebook interruption leaving an independent-session worker alive."""
    import os
    import sys

    import psutil

    from tutorials.supplementary.pet.demo import run_demo

    path, experiment = project
    script = path / "scripts/run-pet.sh"
    # This test substitutes a process-tree fixture, not a generated Pet launcher.
    # Binding mismatch refusal is covered separately by the handoff regressions.
    monkeypatch.setattr(
        "tutorials.supplementary.pet.demo.validate_launcher", lambda *args: None
    )
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-only-not-sent")
    worker = path / "worker.py"
    marker = path / "child.pid"
    worker.write_text(
        "import pathlib,subprocess,sys,time\nchild=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True)\npathlib.Path(sys.argv[1]).write_text(str(child.pid))\ntime.sleep(60)\n"
    )
    import shlex

    script.write_text(
        f"#!/usr/bin/env bash\nexec {shlex.quote(sys.executable)} {shlex.quote(str(worker))} {shlex.quote(str(marker))}\n"
    )
    try:
        with pytest.raises(TimeoutError, match="time limit"):
            run_demo(experiment, script, timeout_seconds=1)
        pid = int(marker.read_text())
        assert (
            not psutil.pid_exists(pid)
            or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
        )
    finally:
        if marker.exists():
            try:
                os.kill(int(marker.read_text()), 9)
            except ProcessLookupError:
                pass


def test_image_preview_uses_user_task_pipeline(project, tmp_path):
    """Catch a notebook showing repository transforms after the user edits theirs."""
    import os
    import sys

    from PIL import Image

    _, experiment = project
    settings = PetExperiment.model_validate_json(experiment.read_text())
    settings.data_dir.mkdir()
    rows = read_splits(settings.composition)["train"]
    for index in (0, 5, 10, 15, 20, 25):
        row = next(r for r in rows if r.class_index == index)
        Image.new("RGB", (8, 8), (255, 0, 0)).save(
            settings.data_dir / f"{row.image_id}.jpg"
        )
    runtime = settings.composition.parent.parent / "runtime/pets_data_path.py"
    source = runtime.read_text().replace(
        "def decode_and_transform(image_path: str | Path) -> torch.Tensor:\n",
        "def decode_and_transform(image_path: str | Path) -> torch.Tensor:\n    return torch.zeros((3, 144, 144))\n",
    )
    runtime.write_text(source)
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from pathlib import Path; from tutorials.supplementary.pet.demo import show_images; f=show_images(Path(sys.argv[1])); assert all(float(a.images[0].get_array().sum()) == 0 for a in f.axes)",
            str(experiment),
        ],
        cwd=ROOT,
        env={**os.environ, "MPLBACKEND": "Agg", "MPLCONFIGDIR": str(tmp_path / "mpl")},
        capture_output=True,
        text=True,
        check=True,
    )


def test_missing_key_is_actionable_before_notebook_creates_a_log(project, monkeypatch):
    """Catch hiding setup errors in a log that then blocks a corrected launch."""
    from tutorials.supplementary.pet.demo import run_demo

    path, experiment = project
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(
        ValueError, match="Missing exported keys: OPENAI_API_KEY.*Export"
    ):
        run_demo(experiment, path / "scripts/run-pet.sh")
    assert not list((path / "runs").iterdir())
