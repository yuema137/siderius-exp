"""Create and verify the immutable wall-clock budget."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .io import create_json_once, read_json
from .model import DeadlineRecord

AGENT_SECONDS = 24 * 60 * 60
FINALIZATION_SECONDS = 15 * 60
VERSION = "tidmad-coding-agent-deadline-v1"


def load_or_create(path: Path, scheduled_start_epoch: int) -> DeadlineRecord:
    candidate = DeadlineRecord(
        version=VERSION,
        scheduled_start_epoch=scheduled_start_epoch,
        agent_deadline_epoch=scheduled_start_epoch + AGENT_SECONDS,
        systemd_ceiling_epoch=scheduled_start_epoch
        + AGENT_SECONDS
        + FINALIZATION_SECONDS,
    )
    create_json_once(path, candidate.to_dict())
    payload = read_json(path)
    record = DeadlineRecord(
        version=str(payload["version"]),
        scheduled_start_epoch=int(payload["scheduled_start_epoch"]),
        agent_deadline_epoch=int(payload["agent_deadline_epoch"]),
        systemd_ceiling_epoch=int(payload["systemd_ceiling_epoch"]),
    )
    if record != candidate:
        raise RuntimeError(
            "existing deadline differs from requested schedule; clear the drill workspace "
            "before creating a formal-run clock"
        )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--scheduled-start-epoch", type=int, required=True)
    args = parser.parse_args()
    record = load_or_create(args.path, args.scheduled_start_epoch)
    remaining = record.agent_deadline_epoch - int(time.time())
    print(f"deadline={record.agent_deadline_epoch} remaining_seconds={remaining}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
