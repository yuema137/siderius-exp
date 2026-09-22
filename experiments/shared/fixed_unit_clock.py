"""Write-once deadline for a generic experiment-defined unit budget."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class LaunchRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["fixed-unit-clock-v1"] = "fixed-unit-clock-v1"
    started_epoch: int = Field(ge=0)
    deadline_epoch: int = Field(gt=0)
    budget_seconds: int = Field(gt=0)
    preflight: dict[str, JsonValue]

    @model_validator(mode="after")
    def fixed_span(self) -> LaunchRecord:
        if self.deadline_epoch - self.started_epoch != self.budget_seconds:
            raise ValueError("clock span differs from the declared unit budget")
        if self.preflight.get("campaign_seconds") != self.budget_seconds:
            raise ValueError("clock budget differs from the frozen preflight")
        return self


def read_clock(path: Path) -> LaunchRecord | None:
    if path.is_symlink():
        raise ValueError("clock must not be a symlink")
    return (
        LaunchRecord.model_validate_json(path.read_bytes()) if path.exists() else None
    )


def create_clock(
    path: Path, *, preflight: dict[str, JsonValue], started: int
) -> LaunchRecord:
    budget = preflight.get("campaign_seconds")
    if type(budget) is not int or budget <= 0:
        raise ValueError("campaign_seconds must be a positive integer")
    record = LaunchRecord(
        started_epoch=started,
        deadline_epoch=started + budget,
        budget_seconds=budget,
        preflight=preflight,
    )
    descriptor, temporary = tempfile.mkstemp(prefix=".launch-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(record.model_dump_json(indent=2).encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)
    return record
