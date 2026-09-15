from deployments.tidmad_coding_agent_baseline.tools.schedule import timer_text


def test_absolute_stop_timer_uses_persisted_ceiling_epoch():
    rendered = timer_text("stop", 1_900_000_000, "tidmad-baseline-stop.service")

    assert "OnCalendar=@1900000000" in rendered
    assert "Persistent=true" in rendered
    assert "Unit=tidmad-baseline-stop.service" in rendered
