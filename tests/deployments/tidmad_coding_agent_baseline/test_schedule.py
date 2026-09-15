from deployments.tidmad_coding_agent_baseline.tools import schedule
from deployments.tidmad_coding_agent_baseline.tools.schedule import timer_text


def test_absolute_stop_timer_uses_persisted_ceiling_epoch():
    rendered = timer_text("stop", 1_900_000_000, "tidmad-baseline-stop.service")

    assert "OnCalendar=@1900000000" in rendered
    assert "Persistent=true" in rendered
    assert "Unit=tidmad-baseline-stop.service" in rendered


def test_deadline_remains_root_owned_and_agent_readable(tmp_path, monkeypatch):
    deadline = tmp_path / "deadline.json"
    deadline.write_text("{}\n")
    ownership = {}

    def record_chown(path, *, user, group):
        ownership.update(path=path, user=user, group=group)

    monkeypatch.setattr(schedule.shutil, "chown", record_chown)

    schedule._grant_deadline_read(deadline, "science-agent")

    assert ownership == {
        "path": deadline,
        "user": "root",
        "group": "science-agent",
    }
    assert deadline.stat().st_mode & 0o777 == 0o640
