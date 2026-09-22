"""Write-once UTC clock for one independent fixed-workflow unit."""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

UNIT_SECONDS = 24 * 60 * 60


class LaunchRecord(BaseModel):
    """Immutable launch identity and the preflight receipt used at first start."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["tidmad-main-fixed-no-prior-launch-v1"]
    started_epoch: int
    deadline_epoch: int
    started_utc: str
    deadline_utc: str
    preflight: dict[str, Any]

    @model_validator(mode="after")
    def require_one_day(self) -> LaunchRecord:
        if self.deadline_epoch - self.started_epoch != UNIT_SECONDS:
            raise ValueError(
                "NoPrior unit deadline must be exactly 24 hours after launch"
            )
        if self.started_utc != _utc(self.started_epoch) or self.deadline_utc != _utc(
            self.deadline_epoch
        ):
            raise ValueError("NoPrior UTC timestamps disagree with the recorded epoch")
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
    """Publish the first clock atomically and never replace it."""

    record = LaunchRecord(
        version="tidmad-main-fixed-no-prior-launch-v1",
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


class ContinuationRecord(BaseModel):
    """One reviewed outage exclusion, without rewriting the original launch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["tidmad-main-fixed-continuation-v1"]
    original_launch_sha256: str
    original_started_epoch: int
    stopped_epoch: int
    started_epoch: int
    deadline_epoch: int
    recovery_evidence_sha256: str
    preflight: dict[str, Any]

    @model_validator(mode="after")
    def require_remaining_budget(self) -> ContinuationRecord:
        consumed = self.stopped_epoch - self.original_started_epoch
        if not 0 < consumed < UNIT_SECONDS:
            raise ValueError(
                "continuation requires a partially consumed original budget"
            )
        if self.started_epoch < self.stopped_epoch:
            raise ValueError("continuation cannot start before the recorded failure")
        if self.deadline_epoch - self.started_epoch != UNIT_SECONDS - consumed:
            raise ValueError(
                "continuation deadline must deduct all previously elapsed time"
            )
        return self


def publish_continuation(path: Path, record: ContinuationRecord) -> None:
    """Atomically publish a separate clock; never replace either launch record."""
    descriptor, name = tempfile.mkstemp(prefix=".continuation-", dir=path.parent)
    temporary = Path(name)
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
