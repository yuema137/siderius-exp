"""Task and experiment ownership checks for the separated TIDMAD package."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path


EXP_ROOT = Path(__file__).resolve().parents[3]
PACK = EXP_ROOT / "tasks" / "tidmad"
COMPOSITION = PACK / "compositions" / "bounded_qualification.yaml"
EXPERIMENT = EXP_ROOT / "experiments" / "tidmad" / "two_iteration_qualification"
LAUNCHER = EXPERIMENT / "launch.sh"


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    checkout = Path(configured).resolve()
    assert (checkout / "sdsc_submission_scripts" / "run_chain.sh").is_file()
    return checkout


def test_task_package_contains_no_qualification_launcher() -> None:
    """Static task ownership must not absorb qualification treatment values."""
    assert not (PACK / "quickstart.sh").exists()
    assert not (PACK / "workflows" / "qualification").exists()
    assert COMPOSITION.is_file()
    assert LAUNCHER.is_file()


def test_experiment_dry_run_preserves_the_qualification_treatment(
    tmp_path: Path,
) -> None:
    """The experiment must select the task scope and exact bounded treatment."""
    checkout = _siderius_checkout()
    workspace = tmp_path / "workspace"
    data_dir = tmp_path / "tidmad"
    data_dir.mkdir()
    (data_dir / "abra_training_0000.h5").touch()
    (data_dir / "abra_validation_0000.h5").touch()
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(Path(sys.executable).resolve().parents[1])

    completed = subprocess.run(
        [
            "bash",
            str(LAUNCHER),
            "--siderius-checkout",
            str(checkout),
            "--workspace",
            str(workspace),
            "--data_dir",
            str(data_dir),
            "--dry-run",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = [
        shlex.split(line.strip())
        for line in completed.stdout.splitlines()
        if "run_one_iteration.py" in line
    ]
    assert len(commands) == 2
    expected_values = {
        "--run_name": "tidmad_quickstart",
        "--max_rounds": "2",
        "--max_epochs": "1",
        "--min_formal_batch_size": "1",
        "--trial_portion": "0.02",
        "--formal_portion": "0.02",
        "--formal_eval_portion": "0.02",
        "--trial_time_budget_minutes": "20",
        "--formal_time_budget_minutes": "60",
    }
    for index, command in enumerate(commands, start=1):
        assert command[command.index("--start_iteration") + 1] == str(index)
        assert command[command.index("--task_composition") + 1] == str(COMPOSITION)
        for flag, expected in expected_values.items():
            assert command[command.index(flag) + 1] == expected
