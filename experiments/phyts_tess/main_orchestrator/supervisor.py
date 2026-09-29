"""Run an external caller under the same immutable clock the chain gets.

The fixed workflow's six hours are enforced by a write-once clock and a
supervisor that kills the process group at the deadline. Without an
equivalent here, the orchestration condition's "six hours" would mean
something else — the launcher policy bounds one native invocation, not the
time a caller spends thinking between them — and the two conditions would
not be comparable on the axis the experiment holds fixed.

**The clock is imported, not copied.** `UNIT_SECONDS` and the write-once
record come from `main_fixed_workflow/unit_clock.py`, so the two conditions
share one budget by construction: change it there and both change. A second
copy would let them drift while both still looked correct.

One consequence of importing rather than forking: the record's `version`
string still reads `phyts-tess-main-fixed-launch-v1`. That names the record
FORMAT, which is genuinely the same, and rewriting the literal would change
a file the `nop_004` lane already merged and whose records already carry it.

This is not the fixed workflow's supervisor and must not become one. It
starts no chain and selects no actions; it runs the command the operator
gives it, which is the caller's own entry point.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from experiments.phyts_tess.main_fixed_workflow.unit_clock import (
    UNIT_SECONDS,
    create_launch_record,
    read_launch_record,
)

__all__ = ["UNIT_SECONDS", "run_unit"]

_HALTED_MARKER = ".caller_halted"


def _append_event(path: Path, event: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")


def run_unit(
    *,
    unit_dir: Path,
    command: list[str],
    preflight: dict[str, Any],
    launch: bool,
) -> int:
    """Start or resume one orchestration unit against its own deadline."""
    unit_dir = unit_dir.resolve()
    if not command:
        raise ValueError("a caller command is required")

    record = read_launch_record(unit_dir / "launch.json")
    if not launch:
        print("command:", " ".join(command))
        print(f"unit budget: {UNIT_SECONDS} s ({UNIT_SECONDS / 3600:.0f} h)")
        if record is None:
            print("clock: not yet started; --launch would create it")
        else:
            print(f"clock: already running, deadline {record.deadline_utc}")
        return 0

    events = unit_dir / "events.jsonl"
    if record is None:
        unit_dir.mkdir(parents=True, exist_ok=True)
        record = create_launch_record(
            unit_dir / "launch.json", preflight, int(time.time())
        )
        _append_event(
            events, {"event": "unit_created", "deadline_utc": record.deadline_utc}
        )
    else:
        # A restart continues against the SAME deadline. A unit that
        # restarted three times must not quietly receive three budgets.
        _append_event(events, {"event": "resumed", "deadline_utc": record.deadline_utc})

    if (unit_dir / _HALTED_MARKER).exists():
        _append_event(events, {"event": "refused_halted_unit"})
        print(f"{_HALTED_MARKER} is present; this unit has stopped for good")
        return 3

    logs = unit_dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    remaining = record.deadline_epoch - time.time()
    if remaining <= 0:
        _append_event(events, {"event": "deadline_already_passed"})
        return 0

    _append_event(
        events,
        {
            "event": "caller_start",
            "started_epoch": int(time.time()),
            "deadline_epoch": record.deadline_epoch,
        },
    )
    descriptor = os.open(
        logs / "caller.log",
        os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "ab", buffering=0) as output:
        process = subprocess.Popen(
            command,
            stdout=output,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            # Its own session, so the deadline kills the whole tree rather
            # than only the process that happens to sit on top of it.
            start_new_session=True,
            cwd=str(unit_dir),
        )
        try:
            returncode = process.wait(timeout=max(0.0, remaining))
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            _append_event(
                events, {"event": "deadline_stop", "ended_epoch": int(time.time())}
            )
            return 0

    _append_event(
        events,
        {
            "event": "caller_exit",
            "ended_epoch": int(time.time()),
            "returncode": returncode,
        },
    )
    return 0 if returncode == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit_dir", type=Path, required=True)
    parser.add_argument("--launch", action="store_true")
    parser.add_argument(
        "command", nargs=argparse.REMAINDER, help="the caller's own entry point"
    )
    args = parser.parse_args(argv)

    command = [item for item in args.command if item != "--"]
    return run_unit(
        unit_dir=args.unit_dir,
        command=command,
        preflight={"condition": "O-NoPrior", "caller_command": command},
        launch=args.launch,
    )


if __name__ == "__main__":
    raise SystemExit(main())
