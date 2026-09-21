"""Agent-visible / evaluator-private view separation for PhyTS TESS.

The defect these guard is specific and cheap to hit: a coding agent has a
shell, so any validation target under a path it can read is a winning
strategy. It copies them into its predictions and scores a perfect
R-squared, and nothing downstream reports a problem — the deliverable is
well formed, scoreable and complete.

Nothing else in this repository can see that. The SIDERIUS-workflow tests
are all correct about a chain whose agent never touches the filesystem, and
the scoreability contract is about the artifact's integrity, not about where
the numbers came from.
"""

from __future__ import annotations

import csv
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

EXP_ROOT = Path(__file__).resolve().parents[3]
PACK = EXP_ROOT / "tasks" / "phyts_tess"
TOOL = PACK / "tools" / "build_views.py"
DATA_DIR_ENV = "PHYTS_TESS_DATA_DIR"


def _tool():
    spec = importlib.util.spec_from_file_location("phyts_tess_build_views", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["phyts_tess_build_views"] = module
    spec.loader.exec_module(module)
    return module


def _staged() -> Path:
    configured = os.environ.get(DATA_DIR_ENV)
    if not configured:
        pytest.skip(
            f"{DATA_DIR_ENV} is not set; this case needs the staged run data root. "
            "Skipped means UNVERIFIED, not passed."
        )
    root = Path(configured).resolve()
    assert root.is_dir()
    return root


def test_the_agent_view_carries_no_validation_target(tmp_path):
    """The whole point, asserted on the bytes rather than on the writer.

    `predict.csv` must name every evaluated light curve — otherwise the agent
    cannot know what to produce — while carrying no column that is an answer.
    Both halves matter: a view that dropped the identities would be safe and
    useless.
    """
    data_dir = _staged()
    output = tmp_path / "views"
    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--data_dir",
            str(data_dir),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

    predict = output / "agent" / "manifests" / "predict.csv"
    rows = list(csv.DictReader(predict.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 442, "the agent must know every curve it is scored on"
    assert set(rows[0]) == {"split", "gaia_id", "tic", "sector"}, set(rows[0])
    assert "frot" not in predict.read_text(encoding="utf-8")

    # The training manifest DOES carry targets, deliberately: supervision is
    # not an answer. Asserted so a future "tighten everything" change cannot
    # silently remove the labels the agent trains on.
    train = output / "agent" / "manifests" / "train.csv"
    train_rows = list(csv.DictReader(train.read_text(encoding="utf-8").splitlines()))
    assert len(train_rows) == 3338
    assert all(row["frot"] for row in train_rows)

    # And the evaluator keeps the truth it needs to score with.
    truth = output / "evaluator" / "manifests" / "val_truth.csv"
    truth_rows = list(csv.DictReader(truth.read_text(encoding="utf-8").splitlines()))
    assert len(truth_rows) == 442
    assert all(row["frot"] for row in truth_rows)


def test_a_planted_validation_target_is_refused(tmp_path):
    """The required failing counterexample.

    Without it the assertion above could be checking a property the writer
    happens to satisfy rather than one the guard enforces.
    """
    module = _tool()
    agent = tmp_path / "agent" / "manifests"
    agent.mkdir(parents=True)
    leaked = agent / "predict.csv"
    leaked.write_text(
        "split,gaia_id,tic,sector,frot,frot_err\n"
        "val,1419655367579509376,198419742,16,1.234,0.0385\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="validation answers"):
        module.assert_agent_view_is_answer_free(tmp_path / "agent")


def test_a_training_target_is_not_mistaken_for_an_answer(tmp_path):
    """Supervision must survive the guard.

    A guard that refused every `frot` column would be trivially safe and
    would make the task unlearnable. This pins the distinction the guard is
    actually drawing: the SPLIT decides, not the column name.
    """
    module = _tool()
    agent = tmp_path / "agent" / "manifests"
    agent.mkdir(parents=True)
    (agent / "train.csv").write_text(
        "split,gaia_id,tic,sector,frot,frot_err\n"
        "train,1419655367579509376,198419742,16,1.234,0.0385\n",
        encoding="utf-8",
    )
    module.assert_agent_view_is_answer_free(tmp_path / "agent")


def test_the_output_directory_must_be_fresh(tmp_path):
    """Writing into a populated directory could leave a stale answer file.

    A previous run's evaluator view sitting beside a new agent view is
    exactly the mount mistake this whole split exists to prevent.
    """
    data_dir = _staged()
    output = tmp_path / "views"
    output.mkdir()
    (output / "leftover.txt").write_text("x", encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--data_dir",
            str(data_dir),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "fresh, empty directory" in completed.stdout + completed.stderr
