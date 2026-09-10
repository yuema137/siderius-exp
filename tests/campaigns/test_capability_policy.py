"""Contract tests for reusable campaign capability execution policy."""

from __future__ import annotations

import pytest

from campaigns.capability_policy import (
    CapabilityExecutionPolicy,
    CapabilityExecutionRefused,
)


def test_disabled_capability_refuses_with_its_declared_reason() -> None:
    """A disabled workflow capability must fail before its caller proceeds."""
    policy = CapabilityExecutionPolicy(
        capability="example_report",
        enabled=False,
        disabled_reason="not part of this workflow",
    )

    with pytest.raises(CapabilityExecutionRefused, match="not part of this workflow"):
        policy.require_enabled()


def test_enabled_capability_allows_its_mechanism_to_proceed() -> None:
    """Another workflow can enable the same capability boundary explicitly."""
    policy = CapabilityExecutionPolicy(capability="example_report", enabled=True)

    assert policy.require_enabled() is None
