"""External-package contract checks for Majorana Low-AvsE."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np

from tasks.majorana_low_avse.plugins._majorana_data import _balanced_indices

EXP_ROOT = Path(__file__).resolve().parents[3]
PACK = EXP_ROOT / "tasks" / "majorana_low_avse"
COMPOSITION = PACK / "compositions" / "low_avse.yaml"
LAUNCHER = EXP_ROOT / "experiments" / "majorana_low_avse" / "launch.sh"
EXPECTED_FRAMEWORK_REVISION = (EXP_ROOT / "SIDERIUS_REVISION").read_text().strip()

COMPOSE_CHILD = textwrap.dedent(
    """
    import json, sys
    from pathlib import Path
    checkout = Path(sys.argv[1]).resolve()
    manifest = Path(sys.argv[2]).resolve()
    sys.path.insert(0, str(checkout))
    from workflows.task_composition import compose_run_task_bindings
    composition = compose_run_task_bindings(str(manifest))
    print(json.dumps({
        "data_path": composition.task_data_path.task_data_path_id,
        "metric": [composition.metric.spec.id, composition.metric.spec.direction],
        "secondary": [item.spec.id for item in composition.secondary_metrics],
        "task_type": composition.forward_contract.task_type,
        "classes": composition.forward_contract.num_classes,
        "partitions": composition.dataset_profile.partition_count,
    }, sort_keys=True))
    """
)


def _checkout() -> Path:
    checkout = Path(os.environ["SIDERIUS_CHECKOUT"]).resolve()
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    assert revision == EXPECTED_FRAMEWORK_REVISION
    return checkout


def test_composition_loads_against_exact_framework_pin() -> None:
    completed = subprocess.run(
        [sys.executable, "-c", COMPOSE_CHILD, str(_checkout()), str(COMPOSITION)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout.splitlines()[-1]) == {
        "classes": 2,
        "data_path": "majorana_low_avse",
        "metric": ["energy_matched_roc_auc", "higher"],
        "partitions": 22,
        "secondary": ["ordinary_roc_auc"],
        "task_type": "classification",
    }


def test_bounded_selection_preserves_balance_in_every_energy_bin() -> None:
    labels = np.array([0, 0, 1, 1, 0, 0, 1, 1], dtype=np.uint8)
    energy = np.array([10, 11, 12, 13, 30, 31, 32, 33], dtype=float)
    selected = _balanced_indices(labels, energy, max_samples=6)
    bins = (energy[selected] // 25).astype(int)
    assert selected.size == 6
    for bin_id in np.unique(bins):
        selected_labels = labels[selected][bins == bin_id]
        assert int((selected_labels == 0).sum()) == int((selected_labels == 1).sum())


def test_qualification_has_a_trial_round_before_forced_formal(tmp_path: Path) -> None:
    """One forced-Formal round would silently leave every Trial override unused."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for index in range(16):
        (data_dir / f"MJD_Train_{index}.hdf5").touch()
    for index in range(6):
        (data_dir / f"MJD_Test_{index}.hdf5").touch()
    completed = subprocess.run(
        [
            "bash",
            str(LAUNCHER),
            "--profile",
            "qualification",
            "--literature",
            "on",
            "--siderius-checkout",
            str(_checkout()),
            "--workspace",
            str(tmp_path / "workspace"),
            "--data_dir",
            str(data_dir),
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = [
        shlex.split(line)
        for line in completed.stdout.splitlines()
        if "run_one_iteration.py" in line
    ]
    assert len(commands) == 2
    for command in commands:
        assert command[command.index("--max_rounds") + 1] == "2"
        assert command[command.index("--trial_portion") + 1] == "0.05"
        assert command[command.index("--formal_portion") + 1] == "0.10"


def test_official_train_and_test_event_ids_do_not_overlap() -> None:
    data_dir = Path(os.environ.get("MAJORANA_DATA_DIR", "/home/klz/Data/MAJORANA"))
    if not data_dir.is_dir():
        raise AssertionError(
            "MAJORANA_DATA_DIR must name the verified official release"
        )
    import h5py

    train = []
    test = []
    for path in sorted(data_dir.glob("MJD_Train_*.hdf5")):
        with h5py.File(path, "r") as handle:
            train.append(np.asarray(handle["id"][:], dtype=np.int64))
    for path in sorted(data_dir.glob("MJD_Test_*.hdf5")):
        with h5py.File(path, "r") as handle:
            test.append(np.asarray(handle["id"][:], dtype=np.int64))
    assert len(train) == 16 and len(test) == 6
    assert np.intersect1d(np.concatenate(train), np.concatenate(test)).size == 0
