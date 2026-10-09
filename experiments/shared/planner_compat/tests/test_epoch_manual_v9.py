"""Qualify only the epoch schema delta and preserve the recorded paper ceilings."""

import json
from copy import deepcopy
from importlib.resources import files
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _manuals():
    return json.loads(
        files("siderius_planner_compat")
        .joinpath("fixtures/paper_ligo_boundary.json")
        .read_text()
    )["config_manuals"]


@pytest.mark.parametrize("late", [False, True])
def test_production_manual_restores_frozen_bytes_and_old_profile_refuses(late):
    from agent.planner_strategy import resolve_planner_strategy
    from agent.skills.check_config_format_skill.wrapper import run_skill

    prefix = "legacy-9b78d505cb11-paper" + ("-late" if late else "")
    current = run_skill(None)["data"]
    before = deepcopy(current)
    expected = json.dumps(_manuals()["pre_pr" if late else "historical"], indent=2)
    profile = resolve_planner_strategy(prefix + "-epochs-v9")
    assert profile.render_config_manual(current) == expected
    assert current == before
    previous = resolve_planner_strategy(prefix + "-verifier-v8")
    with pytest.raises(ValueError, match="Unqualified paper configuration manual"):
        previous.render_config_manual(current)
    with pytest.raises(ValueError, match="changed after run preflight"):
        resolve_planner_strategy(prefix + "-epochs-v9", expected=previous.identity)
    changed_assembly = profile.identity.model_copy(update={"assembly_sha256": "0" * 64})
    with pytest.raises(ValueError, match="changed after run preflight"):
        resolve_planner_strategy(prefix + "-epochs-v9", expected=changed_assembly)


@pytest.mark.parametrize("defect", ["maximum", "default", "minimum", "extra", "old"])
def test_unknown_manual_refuses_before_provider_request(defect):
    from agent.planner_strategy import resolve_planner_strategy
    from agent.skills.check_config_format_skill.wrapper import run_skill

    manual = run_skill(None)["data"]
    epochs = manual["schemas"]["TrainConfig"]["properties"]["epochs"]
    if defect in {"maximum", "default", "minimum"}:
        epochs[defect] = 101
    elif defect == "extra":
        manual["schemas"]["TrainConfig"]["properties"]["new_control"] = {
            "type": "boolean"
        }
    else:
        manual = _manuals()["pre_pr"]
    before = deepcopy(manual)
    profile = resolve_planner_strategy("legacy-9b78d505cb11-paper-epochs-v9")
    with pytest.raises(ValueError, match="Unqualified v9 paper configuration manual"):
        profile.render_config_manual(manual)
    assert manual == before


@pytest.mark.parametrize(
    "version", ["v4", "runtime-v5", "preflight-v6", "storage-v7", "verifier-v8"]
)
def test_previous_manual_profiles_do_not_implicitly_accept_new_schema(version):
    from agent.planner_strategy import resolve_planner_strategy
    from agent.skills.check_config_format_skill.wrapper import run_skill

    current = run_skill(None)["data"]
    for era in ("", "-late"):
        previous = resolve_planner_strategy(f"legacy-9b78d505cb11-paper{era}-{version}")
        with pytest.raises(ValueError, match="Unqualified paper configuration manual"):
            previous.render_config_manual(current)


def test_overlay_retains_all_eleven_archived_caps_and_task_profile_mappings():
    archived = json.loads((ROOT / "paper-replay-369.json").read_text())["units"]
    previous = json.loads(
        (ROOT.parent / "runtime_compat/paper-measured-completion-v1.json").read_text()
    )
    current = json.loads((ROOT / "paper-epoch-caps-v1.json").read_text())
    caps = {
        name: "100"
        for name in ("--max_epochs", "--trial_max_epochs", "--formal_max_epochs")
    }
    assert len(current["covered_units"]) == len(archived) == 11
    assert current["launch_parameters"] == previous["launch_parameters"] | caps
    archived_by_id = {unit["run_id"]: unit for unit in archived}
    for actual, old in zip(
        current["covered_units"], previous["covered_units"], strict=True
    ):
        historical = archived_by_id[actual["run_id"]]
        assert {key: historical["launch_parameters"][key] for key in caps} == caps
        late = historical["infra_revision"].startswith(("349b6cd6", "c0467447"))
        expected = (
            "legacy-9b78d505cb11-paper" + ("-late" if late else "") + "-epochs-v9"
        )
        assert actual["llm_configuration"] == {"tune": {"planner_strategy": expected}}
        assert {
            key: value for key, value in actual.items() if key != "llm_configuration"
        } == {key: value for key, value in old.items() if key != "llm_configuration"}
