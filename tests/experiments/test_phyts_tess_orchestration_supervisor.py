"""The orchestration unit gets the same six hours the chain gets.

Each case names a defect nothing else would catch:

* ``test_a_restart_continues_against_the_same_deadline`` — the property the
  clock exists for. A unit that restarted three times would otherwise have
  quietly received three budgets, and every comparison against another unit
  would be meaningless while both still completed and both still produced
  numbers.
* ``test_the_deadline_kills_the_whole_tree`` — the caller spawns children.
  Killing only the process it sits on top of would let training outlive the
  budget, which is exactly what the budget is for.
* ``test_a_halted_unit_is_refused`` — erasing a halt marker to retry would
  convert a refusal into extra budget.
* ``test_the_budget_is_the_fixed_workflow's`` — the two conditions are
  compared on the axis this holds fixed. A second copy of the constant would
  let them drift while both still looked correct.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path

import pytest

from experiments.phyts_tess.main_fixed_workflow import unit_clock
from experiments.phyts_tess.main_orchestrator.supervisor import UNIT_SECONDS, run_unit


def _events(unit_dir: Path) -> list[dict]:
    path = unit_dir / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _quick() -> list[str]:
    return [sys.executable, "-c", "pass"]


def test_the_budget_is_the_fixed_workflows():
    """One constant, imported, so the two conditions cannot drift apart."""
    assert UNIT_SECONDS is unit_clock.UNIT_SECONDS
    assert UNIT_SECONDS == 6 * 60 * 60


def test_a_restart_continues_against_the_same_deadline(tmp_path):
    unit = tmp_path / "unit"

    assert run_unit(unit_dir=unit, command=_quick(), preflight={}, launch=True) == 0
    first = unit_clock.read_launch_record(unit / "launch.json")
    assert first is not None

    time.sleep(1.1)  # so a fresh clock would differ

    assert run_unit(unit_dir=unit, command=_quick(), preflight={}, launch=True) == 0
    second = unit_clock.read_launch_record(unit / "launch.json")
    assert second is not None

    assert second.deadline_epoch == first.deadline_epoch, (
        "the restart received a new deadline; a unit that restarted three "
        "times would have had three budgets"
    )
    kinds = [event["event"] for event in _events(unit)]
    assert kinds.count("unit_created") == 1
    assert "resumed" in kinds


def test_the_deadline_kills_the_whole_tree(tmp_path):
    """A child that outlives its parent must not outlive the budget."""
    unit = tmp_path / "unit"
    unit.mkdir()

    # A valid record whose span is exact but whose deadline is imminent, so
    # the kill path runs in seconds rather than in six hours.
    unit_clock.create_launch_record(
        unit / "launch.json", {}, int(time.time()) - UNIT_SECONDS + 2
    )

    marker = unit / "child.pid"
    program = (
        "import os, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'])\n"
        f"open({str(marker)!r}, 'w').write(str(child.pid))\n"
        "time.sleep(600)\n"
    )
    assert (
        run_unit(
            unit_dir=unit,
            command=[sys.executable, "-c", program],
            preflight={},
            launch=True,
        )
        == 0
    )

    kinds = [event["event"] for event in _events(unit)]
    assert "deadline_stop" in kinds, kinds

    grandchild = int(marker.read_text(encoding="utf-8"))
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(grandchild, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        os.kill(grandchild, signal.SIGKILL)
        pytest.fail(
            f"grandchild {grandchild} survived the deadline; the kill reached "
            "only the process the supervisor started"
        )


def test_a_halted_unit_is_refused(tmp_path):
    unit = tmp_path / "unit"
    unit.mkdir()
    (unit / ".caller_halted").write_text("", encoding="utf-8")

    assert run_unit(unit_dir=unit, command=_quick(), preflight={}, launch=True) == 3
    assert "refused_halted_unit" in [event["event"] for event in _events(unit)]


def test_the_preview_path_starts_no_clock(tmp_path):
    """Previewing must not spend the thing it is previewing."""
    unit = tmp_path / "unit"
    assert run_unit(unit_dir=unit, command=_quick(), preflight={}, launch=False) == 0
    assert not (unit / "launch.json").exists()
