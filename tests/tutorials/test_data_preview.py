"""Training previews must follow edited file membership and never open holdouts."""

import json

import h5py
import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tasks.tidmad.runtime.file_split import FileSplit
from tutorials.paper.data_preview import plot_training_example
from tutorials.paper.tidmad.project import create_project, write_file_split_task


def test_tidmad_preview_follows_saved_training_membership(tmp_path):
    project = tmp_path / "user project"
    create_project(project, tmp_path / "infra")
    with pytest.raises(ValueError, match="file-holdout experiment saved by Quick A"):
        plot_training_example(
            project / "experiments/tidmad-experiment.json", task="tidmad"
        )
    composition = write_file_split_task(
        project / "tasks/tidmad",
        FileSplit(train_files=(2,), validation_files=(0, 1), test_files=(3,)),
    )
    experiment = project / "experiments/tidmad-experiment.json"
    values = json.loads(experiment.read_text())
    values.update(composition=str(composition), protocol="file-holdout")
    experiment.write_text(json.dumps(values))
    with pytest.raises(ValueError, match="data preparation step"):
        plot_training_example(experiment, task="tidmad")
    with pytest.raises(ValueError, match="Choose PREVIEW_ROW from 0 through"):
        plot_training_example(experiment, task="tidmad", row=50000)
    # Only the assigned training file exists. Reading validation/test must fail.
    path = project / "data/band-0-3/abra_training_0002.h5"
    with h5py.File(path, "w") as handle:
        for channel, value in [("channel0001", -7), ("channel0002", 11)]:
            handle.create_dataset(
                f"timeseries/{channel}/timeseries",
                data=np.full(80000, value, dtype=np.int8),
            )
    figure, description = plot_training_example(experiment, task="tidmad", row=1)
    try:
        assert "abra_training_0002.h5" in description and "window 1" in description
        np.testing.assert_array_equal(figure.axes[0].lines[0].get_ydata(), 121)
        np.testing.assert_array_equal(figure.axes[1].lines[0].get_ydata(), 139)
        assert len(figure.axes[0].lines[0].get_ydata()) == 600
    finally:
        plt.close(figure)


def test_notebook_embedded_examples_match_exported_assets():
    """Copied notebooks must retain portable images without relative-path lookup."""
    import base64
    import hashlib
    from pathlib import Path

    from tutorials.paper.runner import ROOT

    examples = ROOT / "tutorials/paper/examples"
    for path in (ROOT / "tutorials/paper/notebooks").glob("*.ipynb"):
        notebook = json.loads(path.read_text())
        attachments = {
            name: bundle
            for cell in notebook["cells"]
            for name, bundle in cell.get("attachments", {}).items()
        }
        assert len(attachments) == 2
        for name, bundle in attachments.items():
            assert (
                base64.b64decode(bundle["image/png"]) == (examples / name).read_bytes()
            )
        task = path.stem.split("_")[1]
        record = json.loads((examples / f"{task}-example.json").read_text())
        for name, expected in record["assets_sha256"].items():
            assert Path(name).name == name
            assert (
                hashlib.sha256((examples / name).read_bytes()).hexdigest() == expected
            )
