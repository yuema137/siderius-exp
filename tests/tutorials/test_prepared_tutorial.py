"""Guard new demo data identities, native flags and bounded download behavior."""

import io
import json
from typing import ClassVar

import numpy as np
import pytest

from tutorials.paper.prepared import data
from tutorials.paper.prepared.data import DatasetRecipe
from tutorials.paper.prepared.http_ranges import HTTPRangeReader
from tutorials.paper.prepared.project import create_project, prepare_demo
from tutorials.paper.prepared.runner import PreparedExperiment, build_command


@pytest.mark.parametrize("task,channels", [("project8", 4), ("ligo", 2)])
def test_demo_pairs_preserve_identity_and_resplit_without_source_edits(
    tmp_path, monkeypatch, task, channels
):
    """Using source-size declarations or transforming an existing FFT again breaks this."""
    project = tmp_path / "user project"
    create_project(project, tmp_path / "infra", task)
    x = np.random.default_rng(4).normal(size=(128, 2, 32)).astype(np.float32)
    val = x[:40].copy()
    values = {
        "train": (x, np.arange(128, dtype=np.float32)[:, None]),
        "validation": (val, np.arange(40, dtype=np.float32)[:, None]),
    }
    ids = {
        key: [f"{key}:{i}" for i in range(len(pair[0]))] for key, pair in values.items()
    }
    monkeypatch.setattr(
        data, "_read_remote", lambda recipe: (values, ids, {"mode": "fixture"})
    )
    composition = data.prepare(
        project, DatasetRecipe(task=task, train_rows=128, validation_rows=40)
    )
    declaration_path = composition.parent.parent / "declared/prepared.json"
    before = declaration_path.read_bytes()
    declaration = json.loads(before)
    assert (
        declaration["train_count"],
        declaration["validation_count"],
        declaration["channels"],
    ) == (128, 40, channels)
    source = project / "data/demo-001"
    raw = (source / "manifest.json").read_bytes()
    other = data.prepare(
        project,
        DatasetRecipe(
            task=task,
            name="new-split",
            train_rows=128,
            validation_rows=40,
            resplit_validation_fraction=0.66,
        ),
        source=source,
    )
    assert (
        declaration_path.read_bytes() == before
        and (source / "manifest.json").read_bytes() == raw
    )
    changed = json.loads((other.parent.parent / "declared/prepared.json").read_text())
    assert (
        changed["train_count"],
        changed["validation_count"],
        changed["channels"],
    ) == (58, 110, channels)
    groups = json.loads((project / "data/new-split/manifest.json").read_text())[
        "row_identities"
    ]
    assert not set(groups["train"]) & set(groups["validation"])
    assert set(groups["train"]) | set(groups["validation"]) == set(
        ids["train"] + ids["validation"]
    )
    with pytest.raises(ValueError, match="already exists"):
        data.prepare(
            project, DatasetRecipe(task=task, train_rows=128, validation_rows=40)
        )


@pytest.mark.parametrize("task", ["project8", "ligo"])
def test_saved_prepared_command_uses_explicit_formal_scope_and_dual_task(
    tmp_path, task
):
    """LIGO lacks a default formal_portion; Project8 must use the dual workflow rules."""
    project = tmp_path / task
    create_project(project, tmp_path / "infra", task)
    entry = project / f"tasks/{task}-demo-001/compositions/regression.yaml"
    entry.parent.mkdir(parents=True)
    entry.write_text("task_health: {none: true}\n")
    files = prepare_demo(
        project, task, name="quick", settings={"formal_train_fraction": 0.5}
    )
    settings = PreparedExperiment.model_validate_json(files.experiment.read_text())
    command = build_command(settings)
    for flag, value in {
        "--formal_training_scope_source": "operator",
        "--formal_portion": "0.5",
        "--formal_train_portion": "1.0",
        "--num_iterations": "3",
        "--train_portion": "1.0",
        "--task_composition": str(entry),
    }.items():
        assert command.count(flag) == 1 and command[command.index(flag) + 1] == value
    rules = json.loads(command[command.index("--workflow_parameter_rules") + 1])[
        "rules"
    ]
    assert rules["train_config.batch_size"] == {"exact": 1}
    assert "--no-data_analysis_enabled" in command
    assert "--ml_lit_review_enabled" in command and "--ml_lit_review_config" in command
    if task == "project8":
        rules = command[command.index("--workflow_parameter_rules") + 1]
        assert '"training_pool_global"' in rules and '"best_validation_loss"' in rules
    assert str(files.experiment) in files.script.read_text()


def test_range_reader_rejects_full_response_before_reading_payload(monkeypatch):
    """A server ignoring Range must never silently download a multi-GB shard."""

    class Response(io.BytesIO):
        status = 200
        headers: ClassVar[dict] = {}

        def read(self, *args):
            pytest.fail("ignored-range payload was consumed")

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    with (
        HTTPRangeReader("https://example.invalid/data", 10**10) as reader,
        pytest.raises(ValueError, match="refusing a full-file download"),
    ):
        reader.read(8)


def test_range_reader_seeks_across_blocks_and_reuses_cache(monkeypatch):
    """HDF5 requires exact random access; a forward-only or off-by-one reader corrupts rows."""
    requested = []
    payload = b"0123456789abcdef"

    class Response(io.BytesIO):
        status = 206

    def fetch(request, **kwargs):
        start, stop = map(int, request.headers["Range"].split("=")[1].split("-"))
        requested.append((start, stop))
        response = Response(payload[start : stop + 1])
        response.headers = {"Content-Range": f"bytes {start}-{stop}/{len(payload)}"}
        return response

    monkeypatch.setattr("urllib.request.urlopen", fetch)
    with HTTPRangeReader(
        "https://example.invalid/data", len(payload), block_size=4
    ) as reader:
        reader.seek(3)
        assert reader.read(6) == b"345678"
        reader.seek(-2, 1)
        assert reader.read(3) == b"789"
        assert len(requested) == 3
