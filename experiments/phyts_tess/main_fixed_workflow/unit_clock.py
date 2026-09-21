"""Write-once UTC clock for one PhyTS TESS fixed-workflow unit.

The unit's wall-clock budget is decided ONCE, at first launch, and is then
immutable. A restart — a crash, an operator resume, a reboot — continues
against the SAME deadline rather than starting a fresh one, which is the
whole point: a unit that restarted three times would otherwise have quietly
received three times its budget, and every comparison against another unit
would be meaningless.

The write-once guarantee is ``os.link``: hard-linking onto an existing path
fails, so a second ``create_launch_record`` cannot overwrite the first even
by racing it.
"""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

#: Six hours, the operator-frozen budget for one PhyTS TESS unit. Asserted
#: rather than merely used: a record whose span is anything else is refused,
#: so a hand-edited or half-written clock cannot silently extend a run.
UNIT_SECONDS = 6 * 60 * 60


class LaunchRecord(BaseModel):
    """Immutable launch identity and the preflight receipt used at first start."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["phyts-tess-main-fixed-launch-v1"]
    started_epoch: int
    deadline_epoch: int
    started_utc: str
    deadline_utc: str
    preflight: dict[str, Any]

    @model_validator(mode="after")
    def require_the_frozen_span(self) -> LaunchRecord:
        if self.deadline_epoch - self.started_epoch != UNIT_SECONDS:
            raise ValueError(
                "PhyTS TESS unit deadline must be exactly "
                f"{UNIT_SECONDS} seconds after launch"
            )
        if self.started_utc != _utc(self.started_epoch) or self.deadline_utc != _utc(
            self.deadline_epoch
        ):
            raise ValueError("UTC timestamps disagree with the recorded epoch")
        return self


def _utc(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def read_launch_record(path: Path) -> LaunchRecord | None:
    """Read the existing clock, refusing incomplete or malformed state."""
    if path.is_symlink():
        raise ValueError(f"launch record must not be a symlink: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"launch record must be a regular file: {path}")
    return LaunchRecord.model_validate_json(path.read_bytes())


def create_launch_record(
    path: Path, preflight: dict[str, Any], started_epoch: int
) -> LaunchRecord:
    """Publish the first clock atomically and never replace it.

    Written to a temporary file, fsynced, then hard-linked into place. The
    link fails if the record already exists, so two racing launches cannot
    both believe they started the unit.
    """
    record = LaunchRecord(
        version="phyts-tess-main-fixed-launch-v1",
        started_epoch=started_epoch,
        deadline_epoch=started_epoch + UNIT_SECONDS,
        started_utc=_utc(started_epoch),
        deadline_utc=_utc(started_epoch + UNIT_SECONDS),
        preflight=preflight,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".launch-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(record.model_dump_json(indent=2).encode() + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)
    return record
