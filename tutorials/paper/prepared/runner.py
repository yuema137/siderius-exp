"""Launch saved Project8/LIGO demo settings through the fixed native workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

from agent.schemas.parameter_rules import ParameterRules
from pydantic import Field, field_validator
from workflows.llm_config import WorkflowLLMConfig

from experiments.shared.framework_pin import (
    verify_framework_pin,
    verify_installed_framework,
)
from experiments.shared.prepared_unit_preflight import verify_prepared_arrays
from experiments.shared.workflow_credentials import required_workflow_api_keys
from tasks.shared.prepared_regression import PreparedDeclaration
from tutorials.paper.runner import (
    ROOT,
    TutorialExperiment,
    child_environment,
    composition_identity,
    disjoint,
    verify_gpu,
)
from tutorials.paper.runner import build_command as shared_command


class PreparedExperiment(TutorialExperiment):
    version: Literal["siderius-prepared-tutorial-v1"] = "siderius-prepared-tutorial-v1"
    task: Literal["project8", "ligo"]
    literature_config: Path
    batch_size: int = Field(default=1, ge=1, le=128)

    @field_validator("literature_config")
    @classmethod
    def absolute_literature(cls, value):
        if not value.is_absolute():
            raise ValueError("literature_config must be an absolute path")
        return value.resolve()


def credential_status(settings: PreparedExperiment) -> dict[str, bool]:
    required = required_workflow_api_keys(
        settings.llm_config, disabled_roles=frozenset({"data_analysis"})
    )
    return {name: bool(os.environ.get(name, "").strip()) for name in sorted(required)}


def build_command(settings: PreparedExperiment) -> list[str]:
    if settings.composition is None or settings.llm_config is None:
        raise ValueError("select the saved external task and LLM routing")
    if not settings.literature_config.is_file() or any(
        not disjoint(settings.literature_config, p)
        for p in (ROOT, settings.infra_checkout)
    ):
        raise ValueError("select your external llm/literature_review.yaml")
    variant = (
        "main_fixed_workflow_dual_representation"
        if settings.task == "project8"
        else "main_fixed_workflow"
    )
    experiment = ROOT / f"experiments/phyts_{settings.task}" / variant
    command = shared_command(
        settings,
        workflow=experiment / "workflow.json",
        treatment_path=experiment / "information_treatment.yaml",
    )
    # Both demos expose user-owned Formal fractions, including LIGO's agent-owned default.
    command[command.index("--formal_training_scope_source") + 1] = "operator"
    if "--formal_train_portion" not in command:
        command += ["--formal_train_portion", "1.0"]
    flag = "--workflow_parameter_rules"
    rules = (
        ParameterRules.model_validate_json(command[command.index(flag) + 1])
        if flag in command
        else ParameterRules()
    )
    values = rules.model_dump(exclude_none=True)["rules"]
    values["train_config.batch_size"] = {"exact": settings.batch_size}
    rendered = ParameterRules.model_validate(values).model_dump_json(exclude_none=True)
    if flag in command:
        command[command.index(flag) + 1] = rendered
    else:
        command.extend([flag, rendered])
    # Tiny demo pools must not undergo a second, agent-chosen per-epoch thinning.
    command += ["--train_portion", "1.0"]
    return command + ["--ml_lit_review_config", str(settings.literature_config)]


def inspect(settings: PreparedExperiment, *, launch=False):
    command = build_command(settings)
    revision = verify_framework_pin(ROOT, settings.infra_checkout)
    verify_installed_framework(revision, ROOT)
    WorkflowLLMConfig.from_json(str(settings.llm_config))
    fingerprint = composition_identity(settings, str(settings.composition))
    declaration = PreparedDeclaration.model_validate_json(
        (settings.composition.parent.parent / "declared/prepared.json").read_text()
    )
    expected = (
        "phyts_project8_energy_dual"
        if settings.task == "project8"
        else "phyts_ligo_chirp_mass"
    )
    if declaration.task_id != expected:
        raise ValueError("experiment task and task declaration do not match")
    keys = credential_status(settings)
    data, gpu = None, None
    if launch:
        if os.geteuid() == 0:
            raise ValueError("launch as a normal user")
        if not all(keys.values()):
            raise ValueError(
                "export missing API keys: "
                + ", ".join(k for k, v in keys.items() if not v)
            )
        data = verify_prepared_arrays(settings.data_dir, declaration.manifest_sha256)
        gpu = verify_gpu(settings)
    return {
        "kind": f"{settings.task}-teaching-demo",
        "scientific_reproduction": False,
        "settings": settings.model_dump(mode="json"),
        "command": command,
        "infra_revision": revision,
        "exp_revision": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "composition_fingerprint": fingerprint,
        "api_key_status": keys,
        "llm_config_sha256": hashlib.sha256(
            settings.llm_config.read_bytes()
        ).hexdigest(),
        "literature_config_sha256": hashlib.sha256(
            settings.literature_config.read_bytes()
        ).hexdigest(),
        "data": data,
        "gpu": gpu,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args()
    settings = PreparedExperiment.model_validate_json(args.experiment.read_text())
    if any(
        not disjoint(args.experiment, p)
        for p in (ROOT, settings.infra_checkout, settings.data_dir, settings.workspace)
    ):
        raise ValueError(
            "save experiment JSON outside source, data and run directories"
        )
    if args.launch:
        from tutorials.paper.preflight import require_ready

        require_ready(settings, task=settings.task)
    receipt = inspect(settings, launch=args.launch)
    if not args.launch:
        if not all(receipt["api_key_status"].values()):
            print(
                "WARNING: required API keys are missing; export them before launch.",
                file=sys.stderr,
            )
        print(json.dumps(receipt, indent=2))
        return
    path = settings.workspace.with_name(settings.workspace.name + ".tutorial.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(receipt, stream, indent=2)
    os.execvpe("bash", receipt["command"], child_environment(settings))


if __name__ == "__main__":
    main()
