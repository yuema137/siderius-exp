"""Install absolute systemd start and stop timers around the persisted deadline."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from .deadline import load_or_create

SUPERVISOR_GROUP = "baseline-results"


def timer_text(description: str, epoch: int, unit: str) -> str:
    return f"""[Unit]
Description={description}

[Timer]
OnCalendar=@{epoch}
AccuracySec=1s
Persistent=true
Unit={unit}

[Install]
WantedBy=timers.target
"""


def action_text(description: str, action: str) -> str:
    return f"""[Unit]
Description={description}

[Service]
Type=oneshot
ExecStart=/bin/systemctl {action} tidmad-coding-agent.service
"""


def _grant_deadline_read(path: Path, agent_group: str) -> None:
    """Keep the immutable clock root-owned while allowing the supervisor to read it."""

    shutil.chown(path, user="root", group=agent_group)
    path.chmod(0o640)


def install_schedule(
    start_epoch: int,
    systemd_root: Path,
    deadline_path: Path,
    agent_group: str = SUPERVISOR_GROUP,
) -> None:
    if os.geteuid() != 0:
        raise PermissionError("schedule installation must run as root")
    deadline = load_or_create(deadline_path, start_epoch)
    _grant_deadline_read(deadline_path, agent_group)
    units = {
        "tidmad-baseline-start.service": action_text(
            "Start the TIDMAD coding-agent baseline", "start"
        ),
        "tidmad-baseline-start.timer": timer_text(
            "Start the TIDMAD coding-agent baseline at the shared UTC barrier",
            deadline.scheduled_start_epoch,
            "tidmad-baseline-start.service",
        ),
        "tidmad-baseline-stop.service": action_text(
            "Stop the TIDMAD coding-agent baseline at its absolute ceiling", "stop"
        ),
        "tidmad-baseline-stop.timer": timer_text(
            "Stop the TIDMAD coding-agent baseline after collection time",
            deadline.systemd_ceiling_epoch,
            "tidmad-baseline-stop.service",
        ),
    }
    systemd_root.mkdir(parents=True, exist_ok=True)
    for name, content in units.items():
        (systemd_root / name).write_text(content)
    drop_in = systemd_root / "tidmad-coding-agent.service.d"
    drop_in.mkdir(parents=True, exist_ok=True)
    (drop_in / "schedule.conf").write_text(
        f'[Service]\nEnvironment="SCHEDULED_START_EPOCH={start_epoch}"\n'
    )
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "enable", "tidmad-coding-agent.service"], check=True)
    subprocess.run(
        [
            "systemctl",
            "enable",
            "--now",
            "tidmad-baseline-start.timer",
            "tidmad-baseline-stop.timer",
            "tidmad-baseline-backup.timer",
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheduled-start-epoch", type=int, required=True)
    parser.add_argument(
        "--systemd-root", type=Path, default=Path("/etc/systemd/system")
    )
    parser.add_argument(
        "--deadline", type=Path, default=Path("/work/state/deadline.json")
    )
    parser.add_argument("--agent-group", default=SUPERVISOR_GROUP)
    args = parser.parse_args()
    install_schedule(
        args.scheduled_start_epoch,
        args.systemd_root,
        args.deadline,
        agent_group=args.agent_group,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
