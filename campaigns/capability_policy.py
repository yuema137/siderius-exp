"""Reusable execution policy for campaign-owned capabilities."""

from __future__ import annotations

from dataclasses import dataclass


class CapabilityExecutionRefused(RuntimeError):
    """A workflow disabled a capability before its side effects began."""


@dataclass(frozen=True, slots=True)
class CapabilityExecutionPolicy:
    """Declare whether one workflow capability may execute.

    The policy belongs to the workflow, not to the reusable mechanism. Public
    side-effecting entry points call :meth:`require_enabled` before reading
    inputs, computing results, or writing artifacts. A different workflow may
    bind the same kind of mechanism to a different policy without changing the
    mechanism itself.
    """

    capability: str
    enabled: bool
    disabled_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.capability.strip():
            raise ValueError("capability must be non-empty")
        if not self.enabled and not (self.disabled_reason or "").strip():
            raise ValueError("a disabled capability requires a refusal reason")

    def require_enabled(self) -> None:
        """Refuse a disabled capability before its mechanism is invoked."""
        if not self.enabled:
            raise CapabilityExecutionRefused(
                f"{self.capability} is disabled: {self.disabled_reason}"
            )
