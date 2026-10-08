"""Protect the Pet learner's saved inputs and independent plotting handoff."""

import json
from pathlib import Path

import pytest

from tutorials.shared.runtime import ROOT
from tutorials.supplementary.pet.demo import review, run_demo
from tutorials.supplementary.pet.project import create_project, save_variant
from tutorials.supplementary.pet.settings import PetExperiment


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "external project with spaces"
    experiment = create_project(root, tmp_path / "infra", tmp_path / "images")
    return root, experiment


def test_save_variant_preserves_edited_parent_and_matching_launch_pair(project):
    root, original = project
    settings = json.loads(original.read_text())
    settings["epochs"] = 17
    original.write_text(json.dumps(settings))
    script = root / "scripts/run-pet.sh"
    before = original.read_bytes(), script.read_bytes()
    copied, launcher = save_variant(
        root, original, name="pet-more-001", changes={"iterations": 4}
    )
    new = PetExperiment.model_validate_json(copied.read_text())
    assert new.iterations == 4 and new.epochs == 17
    assert new.workspace == root / "runs/pet-more-001"
    assert new.run_name == "pet-more-001"
    assert "pet-more-001.json" in launcher.read_text()
    assert (original.read_bytes(), script.read_bytes()) == before
    with pytest.raises(ValueError, match="never overwritten"):
        save_variant(root, original, name="pet-more-001", changes={"iterations": 5})
    assert new == PetExperiment.model_validate_json(copied.read_text())


@pytest.mark.parametrize("entry", [review, run_demo])
@pytest.mark.parametrize(
    "mismatch",
    ["experiment", "checkout", "runner", "relative_experiment", "relative_checkout"],
)
def test_mismatched_script_refused_before_data_keys_or_launch(
    project, monkeypatch, entry, mismatch
):
    root, original = project
    copied, script = save_variant(root, original, name="other", changes={})
    target = copied
    if mismatch in {"relative_experiment", "relative_checkout"}:
        key = "EXPERIMENT" if mismatch == "relative_experiment" else "EXP_CHECKOUT"
        expected = copied if key == "EXPERIMENT" else ROOT
        monkeypatch.chdir(copied.parent if key == "EXPERIMENT" else ROOT)
        relative = copied.name if key == "EXPERIMENT" else "."
        assert Path(relative).resolve() == expected  # resolve alone would accept this.
        script.write_text(
            "\n".join(
                f"{key}='{relative}'" if line.startswith(key + "=") else line
                for line in script.read_text().splitlines()
            )
            + "\n"
        )
    elif mismatch == "experiment":
        target = original
    elif mismatch == "checkout":
        script.write_text(
            script.read_text().replace(str(ROOT), str(root / "wrong-checkout"))
        )
    else:
        script.write_text(
            script.read_text().replace(
                "tutorials.supplementary.pet.runner", "some_other_runner"
            )
        )

    def fail(*args, **kwargs):
        pytest.fail("mismatched launcher reached effectful/data boundary")

    monkeypatch.setattr("tutorials.supplementary.pet.demo.inspect_data", fail)
    monkeypatch.setattr("tutorials.supplementary.pet.runner.require_credentials", fail)
    monkeypatch.setattr("tutorials.shared.saved_run.subprocess.Popen", fail)
    with pytest.raises(ValueError, match="launcher"):
        entry(target, script)
    assert not list((root / "runs").iterdir())


def test_offline_notebook_preserves_saved_edits_and_replots_without_launch(
    project, tmp_path, monkeypatch
):
    """Run the copied learner notebook with test-only JPEGs and native score records."""
    nbformat = pytest.importorskip(
        "nbformat", reason="install the tutorial dependency group"
    )
    nbclient = pytest.importorskip(
        "nbclient", reason="install the tutorial dependency group"
    )
    from ipykernel.kernelspec import install
    from PIL import Image

    from tests.tutorials.test_progress_demo import write_record
    from tutorials.supplementary.pet.data import read_splits

    root, experiment = project
    saved = json.loads(experiment.read_text())
    saved.update(iterations=4, epochs=17)
    experiment.write_text(json.dumps(saved))
    before = experiment.read_bytes()
    settings = PetExperiment.model_validate(saved)
    settings.data_dir.mkdir()
    # Synthetic solid-color JPEGs are test fixtures, never scientific example evidence.
    for rows in read_splits(settings.composition).values():
        for row in rows:
            Image.new("RGB", (8, 8), (row.class_index * 6, 30, 40)).save(
                settings.data_dir / f"{row.image_id}.jpg"
            )
    record = write_record(settings.workspace, iteration=1, score=0.2, health=True)
    payload = json.loads(record.read_text())
    for attempt in payload["all_records"]:
        attempt["metric_result"]["metric_id"] = "accuracy"
        attempt["denoising_score"] = 0.2
    record.write_text(json.dumps(payload))
    monkeypatch.setenv("JUPYTER_PATH", str(root / ".jupyter/share/jupyter"))
    monkeypatch.setenv("JUPYTER_RUNTIME_DIR", str(root / ".jupyter/runtime"))
    monkeypatch.setenv("IPYTHONDIR", str(root / ".ipython"))
    monkeypatch.setenv("MPLCONFIGDIR", str(root / ".matplotlib"))
    monkeypatch.setenv("TUTORIAL_HOME", str(root))
    install(prefix=str(root / ".jupyter"), kernel_name="pet-offline-test")
    notebook = nbformat.read(root / "notebooks/pet_tutorial.ipynb", as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.source = cell.source.replace(
                "RUN_QUICK_DEMO = True", "RUN_QUICK_DEMO = False"
            ).replace("RUN_NATIVE_PREVIEW = True", "RUN_NATIVE_PREVIEW = False")
    # Fail if the notebook ever crosses its explicit live-execution boundary.
    notebook.cells.insert(
        2,
        nbformat.v4.new_code_cell("""
def forbidden(*args, **kwargs):
    raise AssertionError("offline notebook tried to launch")
run_demo = forbidden
import tutorials.supplementary.pet.runner as runner
runner.require_credentials = forbidden
"""),
    )
    nbclient.NotebookClient(
        notebook,
        timeout=120,
        kernel_name="pet-offline-test",
        resources={"metadata": {"path": str(root)}},
    ).execute()
    assert experiment.read_bytes() == before
    output = root / "plots" / settings.run_name
    assert (output / "score-versus-iteration.png").is_file()
    assert "0.2" in (output / "score-versus-iteration.csv").read_text()
    assert not list((root / "runs").glob("*.console.log"))
    assert not list((root / "runs").glob("*.notebook-run.json"))
    # Execute the opt-in save-as cell against the same edited parent, then only plot.
    save_cell = next(
        c
        for c in notebook.cells
        if c.cell_type == "code" and "SAVE_VARIANT = False" in c.source
    )
    save_cell.source = save_cell.source.replace(
        "SAVE_VARIANT = False", "SAVE_VARIANT = True"
    )
    # Re-execute a short notebook: bootstrap, save-as, then independently select old results.
    plot_cell = notebook.cells[-1]
    plot_cell.source = plot_cell.source.replace(
        "PLOT_EXPERIMENT = EXPERIMENT",
        'PLOT_EXPERIMENT = PROJECT / "experiments/pet-demo.json"',
    )
    subset = nbformat.v4.new_notebook(
        cells=[
            notebook.cells[1],
            notebook.cells[2],
            save_cell,
            nbformat.v4.new_code_cell("import matplotlib.pyplot as plt"),
            plot_cell,
        ]
    )
    nbclient.NotebookClient(
        subset,
        timeout=120,
        kernel_name="pet-offline-test",
        resources={"metadata": {"path": str(tmp_path)}},
    ).execute()
    assert experiment.read_bytes() == before
    variant = PetExperiment.model_validate_json(
        (root / "experiments/pet-more-001.json").read_text()
    )
    assert variant.iterations == 4 and variant.epochs == 17
    assert (root / "scripts/run-pet-more-001.sh").is_file()
    assert not variant.workspace.exists()
