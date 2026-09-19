"""Opt-in real user-manager witness for supervisor -> service halt propagation.

RUN_SYSTEMD_HALT_TEST=1 requires an accessible user systemd manager. No host
accounts, installed services, credentials, data or scientific workload are used.
"""

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from experiments.tidmad.main_fixed_workflow.unit_clock import create_launch_record


@pytest.mark.skipif(
    os.environ.get("RUN_SYSTEMD_HALT_TEST") != "1", reason="requires user systemd"
)
def test_actual_service_does_not_restart_after_supervisor_halt(tmp_path):
    """Before repair supervisor returns 1 and the real manager restarts it."""
    root = Path(__file__).resolve().parents[2]
    template = (
        root / "experiments/tidmad/main_fixed_workflow/systemd/tidmad-no-prior@.service"
    )
    settings = {}
    for line in template.read_text().splitlines():
        key, _, value = line.partition("=")
        if key in {"Restart", "RestartPreventExitStatus", "RestartSec"}:
            settings[key] = value
    record = create_launch_record(
        tmp_path / "launch.json",
        {"command": [sys.executable, "-c", "raise SystemExit(3)"]},
        int(time.time()),
    )
    before = (tmp_path / "launch.json").read_bytes()
    child = tmp_path / "supervise.py"
    child.write_text(
        "from pathlib import Path\n"
        "from experiments.tidmad.main_fixed_workflow.supervisor import _run_chain\n"
        "from experiments.tidmad.main_fixed_workflow.unit_clock import read_launch_record\n"
        f"unit = Path({str(tmp_path)!r})\n"
        "raise SystemExit(_run_chain(read_launch_record(unit/'launch.json'), unit))\n"
    )
    unit = "codex-halt-" + uuid.uuid4().hex + ".service"
    argv = [
        "systemd-run",
        "--user",
        "--wait",
        "--unit",
        unit,
        "--property=StartLimitIntervalSec=60",
        "--property=StartLimitBurst=2",
        "--property=RuntimeMaxSec=10",
        "--property=KillMode=control-group",
        f"--property=WorkingDirectory={root}",
    ]
    argv += [f"--property={key}={value}" for key, value in settings.items()]
    # Execute as a module-capable -c child from the exact exp checkout.
    argv += [
        sys.executable,
        "-c",
        f"exec(compile(open({str(child)!r}).read(), {str(child)!r}, 'exec'))",
    ]
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=50, check=False
        )
        state = subprocess.check_output(
            [
                "systemctl",
                "--user",
                "show",
                unit,
                "-p",
                "NRestarts",
                "-p",
                "ExecMainStatus",
                "-p",
                "ActiveState",
            ],
            text=True,
        )
        assert result.returncode != 0, result.stdout + result.stderr
        assert "NRestarts=0" in state, state
        assert "ExecMainStatus=3" in state, state
        assert "ActiveState=failed" in state, state
        assert (tmp_path / "launch.json").read_bytes() == before
        assert record.deadline_epoch > time.time()
        events = [
            json.loads(line)
            for line in (tmp_path / "events.jsonl").read_text().splitlines()
        ]
        assert [e["event"] for e in events] == ["chain_start", "chain_exit"]
    finally:
        subprocess.run(
            ["systemctl", "--user", "stop", unit], capture_output=True, check=False
        )
        subprocess.run(
            ["systemctl", "--user", "reset-failed", unit],
            capture_output=True,
            check=False,
        )
