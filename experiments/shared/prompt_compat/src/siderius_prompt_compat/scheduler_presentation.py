"""Display only the historical scheduler-disabled contract; never alter execution."""

import json
from agent.schemas.parameter_rules import ParameterRules
from agent.schemas.hyperparam_tuning import TaskCompositionRef

_PATH = "train_config.lr_schedule"


def _view(rules: ParameterRules | None) -> ParameterRules | None:
    if rules is None:
        return None
    copied = dict(rules.rules)
    for path, rule in rules.rules.items():
        if path == _PATH or path.startswith(_PATH + "."):
            if path != _PATH or rule.model_dump(mode="json") != {"exact": None}:
                raise ValueError(
                    "Historical scheduler presentation requires exact null lr_schedule"
                )
            del copied[path]
    return rules.model_copy(update={"rules": copied})


def render_parameter_rules(
    composition_ref: TaskCompositionRef | None,
    workflow_rules: ParameterRules | None,
) -> str:
    task = (
        composition_ref.model_copy(
            update={"parameter_rules": _view(composition_ref.parameter_rules)}
        )
        if composition_ref is not None
        else None
    )
    return _render(task, _view(workflow_rules))


def _render(
    composition_ref: TaskCompositionRef | None,
    workflow_rules: ParameterRules | None,
) -> str:
    """Frozen pre-scheduler prose; execution uses native ParameterRules unchanged.

    Copied from a72a5ef nodes/ml_model_proposal_agent/parameter_rules.py.
    This is historical presentation, not the authority for current rule wording.
    """
    task_rules = (
        composition_ref.parameter_rules if composition_ref is not None else None
    )
    lines = ["## Machine-enforced candidate parameter rules"]
    for owner, rules in (("task", task_rules), ("workflow", workflow_rules)):
        if rules is None:
            continue
        for path, rule in sorted(rules.rules.items()):
            value = rule.model_dump(mode="json")[rule.kind]
            lines.append(
                f"- {owner} {path}: {rule.kind} {json.dumps(value, sort_keys=True)}"
            )
    if len(lines) == 1:
        return ""
    lines.append(
        "Exact values become the effective baseline before the resource preflight; "
        "other rules validate supplied values. Include every known model input "
        "dimension in baseline_config."
    )
    return "\n".join(lines)
