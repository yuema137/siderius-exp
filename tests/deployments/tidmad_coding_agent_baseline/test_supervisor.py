from __future__ import annotations

import json

from deployments.tidmad_coding_agent_baseline.tools import supervisor
from deployments.tidmad_coding_agent_baseline.tools.model import DeadlineRecord


def test_normal_agent_exit_restarts_until_one_fixed_deadline(tmp_path, monkeypatch):
    work = tmp_path / "work"
    prompt = tmp_path / "task.md"
    prompt.write_text("continue existing work")
    deadline = DeadlineRecord("test", 100, 105, 120)
    times = iter((100, 100, 101, 102, 102, 103, 104, 105))
    invocations = []

    monkeypatch.setattr(supervisor, "load_or_create", lambda *_args: deadline)
    monkeypatch.setattr(supervisor, "_wait_for_start", lambda *_args: None)
    monkeypatch.setattr(supervisor.time, "time", lambda: next(times))
    monkeypatch.setattr(supervisor.time, "sleep", lambda *_args: None)
    monkeypatch.setattr(
        supervisor,
        "_run_once",
        lambda **kwargs: (invocations.append(kwargs) or 0, False),
    )

    supervisor.supervise(
        product="codex", work_root=work, prompt=prompt, scheduled_start_epoch=100
    )

    assert len(invocations) == 2
    receipts = [
        json.loads(line)
        for line in (work / "state" / "invocations.jsonl").read_text().splitlines()
    ]
    assert [item["invocation"] for item in receipts] == [1, 2]
    assert all(call["deadline_epoch"] == 105 for call in invocations)
