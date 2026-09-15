"""Small typed records shared by the baseline deployment tools."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal

BANDS = ("0-3", "4-9", "10-14", "15-19")
AgentProduct = Literal["codex", "claude"]


def utc_text(timestamp: float) -> str:
    """Return a stable UTC representation for a Unix timestamp."""

    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class DeadlineRecord:
    """The create-once experiment clock shared across process restarts."""

    version: str
    scheduled_start_epoch: int
    agent_deadline_epoch: int
    systemd_ceiling_epoch: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.update(
            scheduled_start_utc=utc_text(self.scheduled_start_epoch),
            agent_deadline_utc=utc_text(self.agent_deadline_epoch),
            systemd_ceiling_utc=utc_text(self.systemd_ceiling_epoch),
        )
        return payload
