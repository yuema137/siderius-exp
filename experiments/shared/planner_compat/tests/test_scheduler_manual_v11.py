"""Historical schema projection refuses unqualified or scheduled evidence."""

import json
from copy import deepcopy
from importlib.resources import files

import pytest


@pytest.mark.parametrize("late", [False, True])
def test_actual_scheduler_manual_restores_frozen_bytes(late):
    from agent.planner_strategy import resolve_planner_strategy
    from agent.skills.check_config_format_skill.wrapper import run_skill

    prefix = "legacy-9b78d505cb11-paper" + ("-late" if late else "")
    profile = resolve_planner_strategy(prefix + "-scheduler-off-v11")
    manual = run_skill(None)["data"]
    before = deepcopy(manual)
    fixture = json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/paper_ligo_boundary.json")
        .read_text()
    )
    expected = fixture["config_manuals"]["pre_pr" if late else "historical"]
    assert profile.render_config_manual(manual) == json.dumps(expected, indent=2)
    assert manual == before
    manual["schemas"]["TrainConfig"]["properties"]["epochs"]["default"] = 999
    with pytest.raises(ValueError, match="Unqualified v11"):
        profile.render_config_manual(manual)


@pytest.mark.parametrize(
    "record",
    [
        {
            "params": {
                "train_config": {
                    "lr_schedule": {"kind": "step", "step_size_epochs": 2, "gamma": 0.5}
                }
            }
        },
        {
            "proposed_config": {
                "train_config": {
                    "lr_schedule": {"kind": "cosine", "horizon_epochs": 4, "min_lr": 0}
                }
            }
        },
        {"training_history": {"learning_rates": [[0.01]]}},
    ],
)
def test_enabled_evidence_refuses_before_historical_rendering(record):
    from agent.planner_strategy import resolve_planner_strategy

    profile = resolve_planner_strategy("legacy-9b78d505cb11-paper-scheduler-off-v11")
    before = deepcopy(record)
    with pytest.raises(ValueError, match="Historical scheduler-disabled"):
        profile.user_renderer(memory_history=[record])
    assert record == before
