from __future__ import annotations

import json

import pytest

from deployments.tidmad_coding_agent_baseline.tools.deadline import (
    AGENT_SECONDS,
    FINALIZATION_SECONDS,
    load_or_create,
)


def test_deadline_is_reused_and_cannot_move_after_restart(tmp_path):
    path = tmp_path / "state" / "deadline.json"
    original = load_or_create(path, 1_800_000_000)
    original_bytes = path.read_bytes()

    resumed = load_or_create(path, 1_800_000_000)

    assert resumed == original
    assert path.read_bytes() == original_bytes
    assert resumed.agent_deadline_epoch - resumed.scheduled_start_epoch == AGENT_SECONDS
    assert (
        resumed.systemd_ceiling_epoch - resumed.agent_deadline_epoch
        == FINALIZATION_SECONDS
    )
    with pytest.raises(RuntimeError, match="existing deadline differs"):
        load_or_create(path, 1_800_000_001)
    assert json.loads(path.read_text())["scheduled_start_epoch"] == 1_800_000_000
