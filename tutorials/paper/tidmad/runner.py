"""Preview or launch one-band TIDMAD runs; no notebook-side execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import model_validator
from workflows.llm_config import WorkflowLLMConfig

from experiments.shared.framework_pin import (
    verify_framework_pin,
    verify_installed_framework,
)
from experiments.shared.workflow_credentials import required_workflow_api_keys
from experiments.tidmad.main_fixed_workflow.band_inputs import verify_band_inputs
from tasks.tidmad.runtime.file_split import FileSplit
from tutorials.paper.runner import (
    ROOT,
    TutorialExperiment,
    child_environment,
    composition_identity,
    disjoint,
    verify_gpu,
)
from tutorials.paper.runner import (
    build_command as shared_command,
)


class TidmadExperiment(TutorialExperiment):
    version: Literal["siderius-tidmad-tutorial-v1"] = "siderius-tidmad-tutorial-v1"
    protocol: Literal["paper-pool", "file-holdout"] = "paper-pool"
    formal_train_fraction: float = 0.1

    @model_validator(mode="after")
    def protocol_fraction(self):
        if self.protocol == "paper-pool" and self.formal_train_fraction != 0.1:
            raise ValueError(
                "paper-pool Formal is the entire frozen 20/200 pool: keep .1; use a new file-holdout task to change its population"
            )
        if not 0 < self.formal_train_fraction <= 1:
            raise ValueError("formal_train_fraction must be in (0,1]")
        return self


def selected_split(settings: TidmadExperiment) -> FileSplit | None:
    if settings.composition is None:
        raise ValueError("select your external task composition")
    declaration = yaml.safe_load(settings.composition.read_text())["task_data_path"]
    expected = (
        "TidmadFrozenPoolDataPath"
        if settings.protocol == "paper-pool"
        else "FileSplitDataPath"
    )
    if declaration["symbol"] != expected:
        raise ValueError(f"{settings.protocol} requires {expected}")
    return (
        FileSplit.model_validate(declaration["config"]["split"])
        if settings.protocol == "file-holdout"
        else None
    )


def build_command(settings: TidmadExperiment) -> list[str]:
    split = selected_split(settings)
    health_files = (
        "0-3" if split is None else ",".join(map(str, sorted(split.validation_files)))
    )
    return shared_command(
        settings,
        workflow=ROOT / "experiments/tidmad/main_fixed_workflow/workflow.json",
        treatment_path=ROOT
        / "experiments/tidmad/information_treatments/main-fixed-no-prior.yaml",
    ) + ["--data_scope", "0-3", "--health_gate_files", health_files]


def credential_status(settings: TidmadExperiment) -> dict[str, bool]:
    required = required_workflow_api_keys(
        settings.llm_config, disabled_roles=frozenset({"data_analysis"})
    )
    return {name: bool(os.environ.get(name, "").strip()) for name in sorted(required)}


def inspect(settings: TidmadExperiment, *, launch: bool = False) -> dict:
    command = build_command(settings)
    revision = verify_framework_pin(ROOT, settings.infra_checkout)
    verify_installed_framework(revision, ROOT)
    if settings.llm_config is None:
        raise ValueError("select an external LLM routing file")
    WorkflowLLMConfig.from_json(str(settings.llm_config))
    keys = credential_status(settings)
    fingerprint = composition_identity(settings, str(settings.composition))
    data = None
    gpu = None
    if launch:
        if os.geteuid() == 0:
            raise ValueError("launch as a normal user")
        missing = [key for key, present in keys.items() if not present]
        if missing:
            raise ValueError(
                f"export required keys in this terminal: {', '.join(missing)}; never save them in notebooks/configuration"
            )
        data = verify_band_inputs(ROOT, settings.data_dir, "0-3")
        gpu = verify_gpu(settings)
    return {
        "kind": "tidmad-teaching-demo",
        "scientific_reproduction": False,
        "settings": settings.model_dump(mode="json"),
        "infra_revision": revision,
        "exp_revision": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "command": command,
        "api_key_status": keys,
        "composition_fingerprint": fingerprint,
        "llm_config_sha256": hashlib.sha256(
            settings.llm_config.read_bytes()
        ).hexdigest(),
        "data": data,
        "gpu": gpu,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args()
    settings = TidmadExperiment.model_validate_json(args.experiment.read_text())
    if any(
        not disjoint(args.experiment, repo) for repo in (ROOT, settings.infra_checkout)
    ) or any(
        args.experiment.resolve().is_relative_to(p)
        for p in (settings.workspace, settings.data_dir)
    ):
        raise ValueError("keep the experiment outside sources, data and run output")
    receipt = inspect(settings, launch=args.launch)
    if not args.launch:
        missing = [k for k, v in receipt["api_key_status"].items() if not v]
        if missing:
            print(
                "WARNING: missing exported keys: "
                + ", ".join(missing)
                + "; --launch will refuse. Never store values in notebooks/configs.",
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
