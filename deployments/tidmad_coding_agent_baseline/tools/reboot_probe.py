"""Record and verify the mandatory VM-reboot recovery drill."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .io import atomic_write_json, sha256_file

BOOT_ID = Path("/proc/sys/kernel/random/boot_id")


def record_before(deadline: Path, receipt: Path, service: str, stop_timer: str) -> None:
    if not deadline.is_file():
        raise ValueError(f"deadline is missing: {deadline}")
    atomic_write_json(
        receipt,
        {
            "version": "tidmad-coding-agent-reboot-probe-v1",
            "boot_id_before": BOOT_ID.read_text().strip(),
            "deadline_sha256": sha256_file(deadline),
            "deadline_path": str(deadline),
            "service": service,
            "stop_timer": stop_timer,
        },
    )


def verify_after(receipt: Path) -> None:
    payload = json.loads(receipt.read_text())
    current_boot = BOOT_ID.read_text().strip()
    if current_boot == payload["boot_id_before"]:
        raise RuntimeError("boot ID did not change; a VM reboot was not observed")
    deadline = Path(payload["deadline_path"])
    if sha256_file(deadline) != payload["deadline_sha256"]:
        raise RuntimeError("deadline bytes changed across VM reboot")
    service = payload["service"]
    subprocess.run(["systemctl", "is-enabled", service], check=True, timeout=30)
    subprocess.run(["systemctl", "is-active", service], check=True, timeout=30)
    stop_timer = payload["stop_timer"]
    subprocess.run(["systemctl", "is-enabled", stop_timer], check=True, timeout=30)
    subprocess.run(["systemctl", "is-active", stop_timer], check=True, timeout=30)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    before = subparsers.add_parser("before")
    before.add_argument(
        "--deadline", type=Path, default=Path("/work/state/deadline.json")
    )
    before.add_argument(
        "--receipt", type=Path, default=Path("/work/harness/reboot-probe.json")
    )
    before.add_argument("--service", default="tidmad-coding-agent.service")
    before.add_argument("--stop-timer", default="tidmad-baseline-stop.timer")
    after = subparsers.add_parser("after")
    after.add_argument(
        "--receipt", type=Path, default=Path("/work/harness/reboot-probe.json")
    )
    args = parser.parse_args()
    if args.action == "before":
        record_before(args.deadline, args.receipt, args.service, args.stop_timer)
    else:
        verify_after(args.receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
