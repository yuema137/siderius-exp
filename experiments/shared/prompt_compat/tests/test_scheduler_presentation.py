"""Explicit historical off selection is enforced before baseline presentation."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from siderius_prompt_compat.scheduler_presentation import render_parameter_rules

from agent.prompt_rendering import bind_prompt_profile, resolve_prompt_profile
from agent.schemas.parameter_rules import ParameterRules
from nodes.ml_model_proposal_agent.parameter_rules import (
    render_proposal_parameter_rules,
    resolve_proposal_baseline_config,
)
from workflows.run_config import WorkflowLaunchConfig

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("version", [1, 2])
def test_all_overlay_choices_lock_an_enabled_proposal_off_and_preserve_other_rules(
    version,
):
    overlay = json.loads((ROOT / f"profiles/paper-scheduler-disabled-v{version}.json").read_text())
    original = {
        "train_config": {
            "epochs": 1,
            "lr_schedule": {"kind": "step", "step_size_epochs": 2, "gamma": 0.5},
        }
    }
    before = deepcopy(original)
    # Frozen pre-scheduler wording must not follow the changing native renderer.
    old_text = (
        "## Machine-enforced candidate parameter rules\n"
        "- workflow train_config.epochs: exact 7\n"
        "Exact values become the effective baseline before the resource preflight; "
        "other rules validate supplied values. Include every known model input "
        "dimension in baseline_config."
    )
    for selection in overlay["cases"].values():
        launch_data = deepcopy(selection["workflow_launch_overlay"])
        launch_data["workflow_parameter_rules"]["train_config.epochs"] = {"exact": 7}
        launch_data["workflow_parameter_rules"] = ParameterRules.model_validate(
            launch_data["workflow_parameter_rules"]
        )
        launch = WorkflowLaunchConfig(**launch_data)
        effective = resolve_proposal_baseline_config(
            original,
            composition_ref=None,
            workflow_rules=launch.workflow_parameter_rules,
        )
        assert effective["train_config"] == {"epochs": 7, "lr_schedule": None}
        assert original == before
        native_text = render_proposal_parameter_rules(None, launch.workflow_parameter_rules)
        assert "lr_schedule: exact null" in native_text
        with bind_prompt_profile(
            resolve_prompt_profile(selection["task_composition_overlay"]["prompt_renderer"])
        ):
            assert (
                render_proposal_parameter_rules(None, launch.workflow_parameter_rules) == old_text
            )
        assert launch.workflow_parameter_rules.rules["train_config.lr_schedule"].exact is None


@pytest.mark.parametrize(
    "rules",
    [
        {
            "train_config.lr_schedule": {
                "exact": {"kind": "step", "step_size_epochs": 2, "gamma": 0.5}
            }
        },
        {"train_config.lr_schedule.kind": {"exact": "step"}},
        {"train_config.lr_schedule": {"allowed": [None]}},
    ],
)
def test_unqualified_scheduler_rules_are_not_silently_hidden(rules):
    parsed = ParameterRules.model_validate(rules)
    before = parsed.model_dump(mode="json")
    with pytest.raises(ValueError, match="exact null"):
        render_parameter_rules(None, parsed)
    assert parsed.model_dump(mode="json") == before


def test_previous_qualified_assemblies_keep_their_native_appendix(monkeypatch):
    import siderius_prompt_compat as installed

    qualification = json.loads(
        (Path(installed.__file__).parent / "qualification-v2.json").read_text()
    )
    scheduler_disabled = set(qualification["scheduler_disabled_assemblies"])
    qualified = {qualification["assembly_sha256"]} | {
        row["assembly_sha256"] for row in qualification["additional_assemblies"]
    }
    assert scheduler_disabled and qualified - scheduler_disabled
    for digest in sorted(qualified):
        frozen = digest in scheduler_disabled
        monkeypatch.setattr(installed, "rendering_assembly_digest", lambda digest=digest: digest)
        profile = installed.late_v2()
        assert ("native_training.appendix" in profile.renderers) == frozen
        assert ("native_training.appendix" in profile.native_boundaries) != frozen
        assert ("proposer.parameter_rules" in profile.renderers) == frozen


def test_task_rules_and_original_objects_survive_historical_projection():
    from agent.schemas.hyperparam_tuning import TaskCompositionRef

    task = TaskCompositionRef(
        semantic_fingerprint="offline-witness",
        task_data_path_id="offline-witness",
        task_health_binding=None,
        parameter_rules=ParameterRules.model_validate(
            {
                "model_config.width": {"exact": 16},
                "train_config.lr_schedule": {"exact": None},
            }
        ),
    )
    original = task.model_dump(mode="json")
    workflow = ParameterRules.model_validate({"train_config.epochs": {"exact": 7}})
    text = render_parameter_rules(task, workflow)
    assert "task model_config.width: exact 16" in text
    assert "workflow train_config.epochs: exact 7" in text
    assert "lr_schedule" not in text
    assert task.model_dump(mode="json") == original
