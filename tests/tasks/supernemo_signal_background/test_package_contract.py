"""External-package contract checks for SuperNEMO classification."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np

from tasks.supernemo_signal_background.plugins._supernemo_data import _balanced_cap

EXP_ROOT = Path(__file__).resolve().parents[3]
PACK = EXP_ROOT / "tasks" / "supernemo_signal_background"
COMPOSITION = PACK / "compositions" / "signal_background.yaml"
LAUNCHER = EXP_ROOT / "experiments" / "supernemo_signal_background" / "launch.sh"
EXPECTED_FRAMEWORK_REVISION = (
    (EXP_ROOT / "SIDERIUS_REVISION").read_text(encoding="utf-8").strip()
)

COMPOSE_CHILD = textwrap.dedent(
    """
    import json
    import sys
    from pathlib import Path

    checkout = Path(sys.argv[1]).resolve()
    manifest = Path(sys.argv[2]).resolve()
    pack = manifest.parent.parent
    sys.path.insert(0, str(checkout))

    from workflows import task_composition as composition_module
    from workflows.task_composition import compose_run_task_bindings

    source = Path(composition_module.__file__).resolve()
    if not source.is_relative_to(checkout):
        raise RuntimeError(f"source-authority violation: {source}")
    composition = compose_run_task_bindings(str(manifest))
    print(json.dumps({
        "task_data_path_id": composition.task_data_path.task_data_path_id,
        "primary": [composition.metric.spec.id, composition.metric.spec.direction],
        "secondary": [[item.spec.id, item.spec.direction]
                      for item in composition.secondary_metrics],
        "objective": [composition.objective.loss_type,
                      composition.objective.reduction],
        "task_type": composition.forward_contract.task_type,
        "num_classes": composition.forward_contract.num_classes,
        "partitions": composition.dataset_profile.partition_count,
        "health": composition.task_health_binding,
        "task_owned": all(
            Path(path).resolve().is_relative_to(pack)
            for path in [
                *composition.provenance.source_paths.values(),
                *(item.absolute_path for item in composition.provenance.plugins),
            ]
        ),
    }, sort_keys=True))
    """
)


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError("SIDERIUS_CHECKOUT must name the pinned checkout")
    checkout = Path(configured).resolve()
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    assert revision == EXPECTED_FRAMEWORK_REVISION
    return checkout


def test_composition_loads_once_and_owns_its_science() -> None:
    """Metric reuse must not register a second task-data implementation."""
    checkout = _siderius_checkout()
    completed = subprocess.run(
        [sys.executable, "-c", COMPOSE_CHILD, str(checkout), str(COMPOSITION)],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout.splitlines()[-1]) == {
        "health": "explicit_none",
        "num_classes": 2,
        "objective": ["ce", "mean"],
        "partitions": 4,
        "primary": ["energy_matched_roc_auc", "higher"],
        "secondary": [["ordinary_roc_auc", "higher"]],
        "task_data_path_id": "supernemo_signal_background",
        "task_owned": True,
        "task_type": "classification",
    }


def test_max_samples_retains_per_bin_class_balance() -> None:
    """A bounded scope must not turn energy balance into class imbalance."""
    labels = np.array([1, 1, 1, 0, 0, 0, 1, 1, 0, 0], dtype=np.uint8)
    energy = np.array([10, 11, 12, 13, 14, 15, 30, 31, 32, 33], dtype=float)
    indices = np.arange(labels.size)

    selected = _balanced_cap(indices, labels, energy, max_samples=6)

    assert selected.size == 6
    selected_bins = np.searchsorted(np.arange(0.0, 3625.0, 25.0), energy[selected]) - 1
    for bin_id in np.unique(selected_bins):
        in_bin = selected_bins == bin_id
        assert int(labels[selected][in_bin].sum()) * 2 == int(in_bin.sum())


def test_launch_profiles_preserve_the_approved_treatments(tmp_path: Path) -> None:
    """The launcher must transport both bounded qualification and campaign policy."""
    checkout = _siderius_checkout()
    data_dir = tmp_path / "data"
    indexes = data_dir / "event_indexes"
    indexes.mkdir(parents=True)
    for process in ("0nubb", "2nubb", "Bi214", "Tl208"):
        (data_dir / f"data_{process}_merged.h5").touch()
        (indexes / f"{process}_event_index.npz").touch()

    expected = {
        "qualification": {
            "--max_rounds": "2",
            "--max_epochs": "1",
            "--trial_portion": "0.01",
            "--train_portion": "0.01",
            "--eval_portion": "0.01",
            "--formal_portion": "0.01",
            "--formal_train_portion": "0.01",
            "--formal_eval_portion": "0.01",
            "--trial_time_budget_minutes": "1",
            "--formal_time_budget_minutes": "1",
        },
        "campaign": {
            "--max_rounds": "3",
            "--max_epochs": "50",
            "--trial_portion": "0.20",
            "--train_portion": "0.20",
            "--eval_portion": "0.20",
            "--formal_portion": "1.0",
            "--formal_train_portion": "0.20",
            "--formal_eval_portion": "1.0",
            "--trial_time_budget_minutes": "10",
            "--formal_time_budget_minutes": "30",
            "--trial_vram_budget_gb": "10",
            "--formal_vram_budget_gb": "10",
        },
    }
    for profile, values in expected.items():
        completed = subprocess.run(
            [
                "bash",
                str(LAUNCHER),
                "--profile",
                profile,
                "--siderius-checkout",
                str(checkout),
                "--workspace",
                str(tmp_path / profile),
                "--data_dir",
                str(data_dir),
                "--dry-run",
            ],
            cwd=tmp_path,
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
        assert len(commands) == (2 if profile == "qualification" else 20)
        for command in commands:
            for flag, value in values.items():
                assert command[command.index(flag) + 1] == value
            assert json.loads(command[command.index("--plan_overrides") + 1]) == {
                "eval_strategy": "snapshot",
                "trial_strategy": "snapshot",
            }
