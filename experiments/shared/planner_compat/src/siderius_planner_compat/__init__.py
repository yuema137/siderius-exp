"""Historical planner providers; installing this package declares its default."""

import hashlib
import importlib
from dataclasses import replace
from pathlib import Path

from agent.planner_strategy import PlannerStrategy
from core.planner_strategy_identity import PlannerStrategyIdentity, source_fingerprint


def _load(name: str, expected: str) -> PlannerStrategy:
    source = Path(__file__).with_name(name + ".py")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError(f"Historical planner source changed: {name}")
    module = importlib.import_module(f"{__name__}.{name}")
    loss_source = Path(__file__).with_name("legacy_loss_rendering.py")
    if hashlib.sha256(loss_source.read_bytes()).hexdigest() != (
        "9af47ab18d2a2e443023e12d5afc15403a9844a34e2c76459d485d25709882a4"
    ):
        raise ValueError("Historical planner loss-rendering source changed")
    return PlannerStrategy(
        identity=PlannerStrategyIdentity(
            name=name.replace("_", "-") + "-v1",
            version="1",
            content_sha256=source_fingerprint(
                {
                    name + ".py": source.read_bytes(),
                    "__init__.py": Path(__file__).read_bytes(),
                    "legacy_loss_rendering.py": loss_source.read_bytes(),
                }
            ),
        ),
        system_template=module.PLANNER_PROMPT,
        user_renderer=module.get_planner_user_prompt,
        uses_timing_context=False,
        task_renderer=_task_contract,
        system_renderer=_historical_system_template,
    )


def _historical_system_template(template, task_render):
    """Keep conditional historical loss advice in the experiment-owned provider."""
    from .legacy_loss_rendering import render_loss_sections

    for token, section in render_loss_sections(task_render.loss_context).items():
        template = template.replace("{" + token + "}", section)
    return template


def current_legacy() -> PlannerStrategy:
    return _load(
        "legacy_9b78d505cb11", "9b78d505cb11786319aca45e763f48d73d235e0f7e9de6fb3a62ffc774d237bd"
    )


def early_legacy() -> PlannerStrategy:
    return replace(
        _load(
            "legacy_691617f04b42",
            "691617f04b42f8e903188ac6aa701afedc09a54148d0fba826275b6bf794c013",
        ),
        user_renderer=_early_user_renderer,
        task_renderer=_early_task_contract,
    )


def _task_contract(description, context):
    """Retain the source-revision agent-owned Formal task appendix verbatim."""
    if context is None or context.formal_training_scope_source != "agent":
        return description
    return description + (
        "\n\nRUN-SPECIFIC DATA/SCORE CONTRACT: Trial training strategy and fractions "
        "(`trial_portion`, `train_portion`) and Trial validation "
        "fraction (`eval_portion`) are your choices. Formal training "
        "strategy and fractions also come from your validated plan's "
        "`trial_strategy`, `trial_portion` "
        "and `train_portion`; choose them for the Formal round. "
        "Formal validation does not use your `eval_portion`: it is "
        f"operator-fixed at {context.formal_eval_portion:.6g} of "
        "the declared validation scope. A valid full-scope Formal "
        "score is the official comparable result; Trial scores are "
        "development feedback, not the official result."
    )


def _early_user_renderer(*, custom_loss_inventory=None, **arguments):
    """Adapt the historical registry keyword only for an established empty registry.

    A modern task-filtered inventory cannot reconstruct the old registry: it
    can hide entries or report unavailable metadata. Refuse those cases instead
    of dropping information and claiming historical equivalence.
    """
    if custom_loss_inventory is not None and (
        custom_loss_inventory.entries
        or custom_loss_inventory.unavailable
        or custom_loss_inventory.unavailable_reason is not None
    ):
        raise ValueError(
            "The early planner requires a verified historical custom-loss registry. "
            "Only the empty-registry adapter is currently supported. Keep this run "
            "on its original infra revision until the registry migration is qualified."
        )
    module = importlib.import_module(f"{__name__}.legacy_691617f04b42")
    return module.get_planner_user_prompt(registry=None, **arguments)


def _early_task_contract(description, context):
    """The early planning source passed the task description without an appendix."""
    if context is not None and (
        context.formal_training_scope_source != "operator"
        or context.training_validation_portion is not None
    ):
        raise ValueError(
            "The early planner has no qualified migration for agent-owned Formal "
            "training or independent epoch-validation scope. Use the original "
            "configuration and infra revision for historical replay."
        )
    return description
