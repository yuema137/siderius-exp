"""Paper manual qualification must reject drift rather than silently omit facts."""

import json
from copy import deepcopy
from importlib.resources import files

import pytest
from siderius_planner_compat.paper_v4 import historical_paper_late_v4, historical_paper_v4


def test_profiles_restore_revision_specific_manual_and_refuse_new_schema():
    from agent.skills.check_config_format_skill.wrapper import run_skill

    fixture = json.loads(
        files("siderius_planner_compat").joinpath("fixtures/paper_ligo_boundary.json").read_text()
    )
    current = run_skill(None)["data"]
    before = deepcopy(current)
    for provider, manual in [
        (historical_paper_v4(), "historical"),
        (historical_paper_late_v4(), "pre_pr"),
    ]:
        assert provider.render_config_manual(current) == json.dumps(
            fixture["config_manuals"][manual], indent=2
        )
        changed = deepcopy(current)
        changed["schemas"]["TrainConfig"]["properties"]["unqualified_control"] = {"type": "boolean"}
        with pytest.raises(ValueError, match="Unqualified paper configuration manual"):
            provider.render_config_manual(changed)
    assert current == before
