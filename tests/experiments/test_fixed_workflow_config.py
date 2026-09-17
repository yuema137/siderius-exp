"""A fixed workflow has one JSON authority shared by its treatment arms."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from experiments.shared.fixed_workflow_config import render_siderius_args

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "experiments/tidmad/prerelease-tidmad-proof-of-function/workflow.json"


def _fixture(
    tmp_path: Path, *, parameters: dict[str, object]
) -> tuple[Path, Path, Path]:
    experiment_root = tmp_path / "exp"
    siderius_root = tmp_path / "infra"
    composition = experiment_root / "tasks/demo/composition.yaml"
    agent_config = siderius_root / "configs/llm/agents.json"
    composition.parent.mkdir(parents=True)
    agent_config.parent.mkdir(parents=True)
    composition.write_text("task: demo\n")
    agent_config.write_text('{"propose": {"model_id": "test"}}\n')
    config = experiment_root / "experiments/demo/workflow.json"
    config.parent.mkdir(parents=True)
    config.write_text(
        json.dumps(
            {
                "version": "siderius-exp-fixed-workflow-v1",
                "task_composition": "tasks/demo/composition.yaml",
                "agent_parameters": "configs/llm/agents.json",
                "parameters": parameters,
            }
        )
    )
    return config, experiment_root, siderius_root


def test_prerelease_both_advice_treatments_share_one_workflow_json() -> None:
    from experiments.shared.information_treatment import resolve_information_treatment

    treatment_root = ROOT / "experiments/tidmad/information_treatments"
    on = resolve_information_treatment(
        treatment_root / "prerelease-with-advice.yaml",
        repository_root=ROOT,
        adapter="siderius",
    )
    off = resolve_information_treatment(
        treatment_root / "prerelease-without-advice.yaml",
        repository_root=ROOT,
        adapter="siderius",
    )
    workflow = json.loads(WORKFLOW.read_text())
    assert workflow["parameters"]["--num_iterations"] == 10
    assert on.task_package_path == off.task_package_path
    assert "--advice" in on.siderius_args()
    assert "--advice" not in off.siderius_args()
    assert "--advice" not in workflow["parameters"]
    assert "--ml_lit_review_enabled" not in workflow["parameters"]


def test_renderer_binds_composition_agents_and_shared_workflow(tmp_path: Path) -> None:
    config, experiment_root, siderius_root = _fixture(
        tmp_path,
        parameters={
            "--num_iterations": 10,
            "--trial_portion": 0.1,
            "--force_fresh": True,
        },
    )
    assert render_siderius_args(
        config, repository_root=experiment_root, siderius_checkout=siderius_root
    ) == [
        "--task_composition",
        str(experiment_root / "tasks/demo/composition.yaml"),
        "--llm_config",
        str(siderius_root / "configs/llm/agents.json"),
        "--num_iterations",
        "10",
        "--trial_portion",
        "0.1",
        "--force_fresh",
    ]


def test_formal_segmentation_lock_uses_existing_generic_parameter_rules(
    tmp_path: Path,
) -> None:
    from agent.schemas.parameter_rules import ParameterRules

    config, experiment_root, siderius_root = _fixture(tmp_path, parameters={})
    payload = json.loads(config.read_text())
    payload["workflow_parameter_rules"] = {
        "model_config.segmentation_size": {"exact": 40_000}
    }
    config.write_text(json.dumps(payload))
    arguments = render_siderius_args(
        config, repository_root=experiment_root, siderius_checkout=siderius_root
    )
    index = arguments.index("--workflow_parameter_rules")
    assert (
        ParameterRules.model_validate_json(arguments[index + 1])
        .rules["model_config.segmentation_size"]
        .exact
        == 40_000
    )
    assert (
        json.loads(
            (ROOT / "experiments/tidmad/main_fixed_workflow/workflow.json").read_text()
        )["workflow_parameter_rules"]
        == payload["workflow_parameter_rules"]
    )
    from experiments.shared.information_treatment import (
        ModuleState,
        resolve_information_treatment,
    )

    treatment = resolve_information_treatment(
        ROOT / "experiments/tidmad/information_treatments/main-fixed-no-prior.yaml",
        repository_root=ROOT,
        adapter="siderius",
        required_modules=("literature_review", "data_analysis"),
    )
    assert treatment.module_states == {
        "literature_review": ModuleState.ENABLED,
        "data_analysis": ModuleState.DISABLED,
    }
    assert treatment.siderius_args() == [
        "--experiment_arm",
        "tidmad-main-fixed-no-prior-v1",
        "--no-data_analysis_enabled",
        "--ml_lit_review_enabled",
    ]


def test_tidmad_full_no_prior_pair_differs_only_in_analysis_treatment(
    tmp_path: Path,
) -> None:
    """The paired renderer uses PR #80's module state, not a second switch.

    Full is a structural test fixture until its band-scoped analysis binding
    and effectful launcher are qualified by the experiment package.
    """
    from experiments.shared.information_treatment import resolve_information_treatment

    no_prior_path = (
        ROOT / "experiments/tidmad/information_treatments/main-fixed-no-prior.yaml"
    )
    full_payload = yaml.safe_load(no_prior_path.read_text(encoding="utf-8"))
    full_payload["treatment_id"] = "tidmad-main-fixed-full-test-v1"
    full_payload["modules"]["data_analysis"]["siderius"] = "enabled"
    full_path = tmp_path / "main-fixed-full-test.yaml"
    full_path.write_text(yaml.safe_dump(full_payload), encoding="utf-8")

    no_prior = resolve_information_treatment(
        no_prior_path,
        repository_root=ROOT,
        adapter="siderius",
        required_modules=("literature_review", "data_analysis"),
    )
    full = resolve_information_treatment(
        full_path,
        repository_root=ROOT,
        adapter="siderius",
        required_modules=("literature_review", "data_analysis"),
    )
    assert no_prior.task_package_path == full.task_package_path
    assert no_prior.declaration.advice == full.declaration.advice
    assert (
        no_prior.module_states["literature_review"]
        == full.module_states["literature_review"]
    )
    assert no_prior.siderius_args()[2:] == [
        "--no-data_analysis_enabled",
        "--ml_lit_review_enabled",
    ]
    assert full.siderius_args()[2:] == [
        "--data_analysis_enabled",
        "--ml_lit_review_enabled",
    ]


def test_main_full_treatment_binds_reviewed_advice_and_explicit_analysis() -> None:
    from experiments.shared.information_treatment import (
        AdviceMode,
        ModuleState,
        resolve_information_treatment,
    )

    treatment = resolve_information_treatment(
        ROOT / "experiments/tidmad/information_treatments/main-fixed-full.yaml",
        repository_root=ROOT,
        adapter="siderius",
        required_modules=("literature_review", "data_analysis"),
    )
    assert treatment.declaration.advice.mode is AdviceMode.ENABLED
    assert treatment.advice_path == (
        ROOT / "experiments/tidmad/main_fixed_workflow/advice.json"
    )
    assert treatment.module_states == {
        "literature_review": ModuleState.ENABLED,
        "data_analysis": ModuleState.ENABLED,
    }
    args = treatment.siderius_args()
    assert "--data_analysis_enabled" in args
    assert args[args.index("--advice") + 1] == str(treatment.advice_path)


@pytest.mark.parametrize(
    ("parameters", "message"),
    [
        ({"--advice": "other.json"}, "launch-owned"),
        ({"--human_advice_propose": "hidden hint"}, "launch-owned"),
        ({"--no-ml_lit_review_enabled": True}, "launch-owned"),
        ({"--data_analysis_enabled": True}, "launch-owned"),
        ({"--no-data_analysis_enabled": True}, "launch-owned"),
        ({"--workspace": "other"}, "launch-owned"),
        ({"--force_fresh": False}, "must be true"),
        ({"--num_iterations": "10\n--advice"}, "invalid workflow parameter value"),
    ],
)
def test_workflow_json_cannot_override_treatment_or_launch_identity(
    tmp_path: Path, parameters: dict[str, object], message: str
) -> None:
    config, experiment_root, siderius_root = _fixture(tmp_path, parameters=parameters)
    with pytest.raises(ValueError, match=message):
        render_siderius_args(
            config, repository_root=experiment_root, siderius_checkout=siderius_root
        )


def test_duplicate_json_key_is_refused(tmp_path: Path) -> None:
    config, experiment_root, siderius_root = _fixture(tmp_path, parameters={})
    config.write_text(
        config.read_text().replace(
            '"parameters": {}', '"parameters": {}, "parameters": {}'
        )
    )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        render_siderius_args(
            config, repository_root=experiment_root, siderius_checkout=siderius_root
        )


def test_configuration_paths_cannot_escape_either_checkout(tmp_path: Path) -> None:
    config, experiment_root, siderius_root = _fixture(tmp_path, parameters={})
    payload = json.loads(config.read_text())
    payload["agent_parameters"] = "../secrets.json"
    config.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="repository-relative"):
        render_siderius_args(
            config, repository_root=experiment_root, siderius_checkout=siderius_root
        )


def test_main_workflow_keeps_training_agent_chosen_and_formal_eval_full() -> None:
    main = json.loads(
        (ROOT / "experiments/tidmad/main_fixed_workflow/workflow.json").read_text()
    )
    assert main["task_composition"] == (
        "tasks/tidmad/compositions/continuous_regression.yaml"
    )
    assert main["parameters"]["--formal_training_scope_source"] == "agent"
    assert "--formal_portion" not in main["parameters"]
    assert "--trial_portion" not in main["parameters"]
    assert "--train_portion" not in main["parameters"]
    assert "--eval_portion" not in main["parameters"]
    assert main["parameters"]["--formal_eval_portion"] == 1.0


def test_main_workflow_freezes_shared_budget_and_exp_owned_openai_config() -> None:
    main = json.loads(
        (ROOT / "experiments/tidmad/main_fixed_workflow/workflow.json").read_text()
    )
    assert main["agent_parameters_owner"] == "experiment"
    llm = json.loads((ROOT / main["agent_parameters"]).read_text())
    slots = [
        llm["interpret"],
        llm["data_analysis"],
        llm["implement"],
        llm["validate"],
        *llm["propose"].values(),
        *llm["tune"].values(),
        *llm["lit_review"].values(),
    ]
    assert all(
        slot
        == {
            "provider": "openai",
            "model_id": "gpt-5.6-sol",
            "reasoning_effort": "medium",
        }
        for slot in slots
    )
    assert main["parameters"]["--num_iterations"] == 100
    assert main["parameters"]["--max_rounds"] == 3
    assert main["parameters"]["--trial_time_budget_minutes"] == 30
    assert main["parameters"]["--formal_time_budget_minutes"] == 120
    assert main["parameters"]["--trial_vram_budget_gb"] == 40
    assert main["parameters"]["--formal_vram_budget_gb"] == 40
    assert main["parameters"]["--trial_max_epochs"] == 2
    assert main["parameters"]["--formal_max_epochs"] == 2
    assert (
        not {"--trial_portion", "--train_portion", "--eval_portion"}
        & main["parameters"].keys()
    )


def test_main_workflow_renders_exp_owned_llm_config(tmp_path: Path) -> None:
    config, experiment_root, siderius_root = _fixture(tmp_path, parameters={})
    agent_config = experiment_root / "experiments/demo/agents.json"
    agent_config.parent.mkdir(parents=True, exist_ok=True)
    agent_config.write_text('{"interpret": {"provider": "openai"}}')
    payload = json.loads(config.read_text())
    payload["agent_parameters_owner"] = "experiment"
    payload["agent_parameters"] = "experiments/demo/agents.json"
    config.write_text(json.dumps(payload))
    args = render_siderius_args(
        config, repository_root=experiment_root, siderius_checkout=siderius_root
    )
    assert args[args.index("--llm_config") + 1] == str(agent_config)
