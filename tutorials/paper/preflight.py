"""Actionable, secret-free setup checks shared by notebook and shell launchers."""

from __future__ import annotations

import os
import shlex
import shutil
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from tutorials.shared.bootstrap import shell_setup_guard

if TYPE_CHECKING:
    from tutorials.paper.runner import TutorialExperiment


class SetupIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    problem: str
    fix: str


def require_ready(
    settings: TutorialExperiment, *, task: Literal["tess", "tidmad", "project8", "ligo"]
) -> None:
    """Collect cheap setup failures before native hashes/CUDA/pin validation.

    This does not authenticate provider keys or replace native launch checks.
    Values of credentials are never included in diagnostics.
    """
    from tutorials.paper.runner import ROOT, credential_status

    issues: list[SetupIssue] = []

    def add(problem: str, fix: str) -> None:
        issues.append(SetupIssue(problem=problem, fix=fix))

    for checkout, groups in (
        (ROOT, "--group dev --group tutorial"),
        (settings.infra_checkout, "--group dev"),
    ):
        python = checkout / ".venv/bin/python"
        if not python.is_file() or not os.access(python, os.X_OK):
            add(
                f"Missing checkout Python: {python}",
                f"Run: cd {shlex.quote(str(checkout))} && uv sync {groups} --frozen",
            )
    for name, path in (
        ("task composition", settings.composition),
        ("LLM routing", settings.llm_config),
    ):
        if path is None or not path.is_file():
            add(
                f"Missing {name} file: {path}",
                "Restore this file in your external project and set its absolute path in the experiment JSON.",
            )
    if settings.llm_config is not None and settings.llm_config.is_file():
        try:
            if task in ("project8", "ligo"):
                from tutorials.paper.prepared.runner import (
                    credential_status as prepared_keys,
                )

                status = prepared_keys(settings)
            elif task == "tidmad":
                from tutorials.paper.tidmad.runner import credential_status as keys

                status = keys(settings)
            else:
                status = credential_status(settings.llm_config)
            missing = [name for name, present in status.items() if not present]
            if missing:
                add(
                    "Missing exported API keys: " + ", ".join(missing),
                    "Export these names from your trusted external credentials file in the launching terminal. "
                    "For Jupyter, stop the server, export the keys, restart Jupyter and select the exp kernel. "
                    "Never paste secret values into notebook cells, JSON or scripts.",
                )
        except (ValueError, KeyError, OSError):
            add(
                f"Invalid LLM routing: {settings.llm_config}",
                "Restore the project's llm/agents.json template, then edit supported provider/model fields. Do not put API keys in this file.",
            )
    if task in ("project8", "ligo"):
        names = [
            "manifest.json",
            "training/inputs.npy",
            "training/targets.npy",
            "evaluator/validation/inputs.npy",
            "evaluator/validation/targets.npy",
            "evaluator/validation/loss_indices.npy",
        ]
        literature = getattr(settings, "literature_config", None)
        if literature is None or not literature.is_file():
            add(
                f"Missing literature-review configuration: {literature}",
                "Restore llm/literature_review.yaml in your external project.",
            )
    elif task == "tidmad":
        names = [
            f"abra_{family}_{i:04d}.h5"
            for family in ("training", "validation")
            for i in range(4)
        ]
        names.append("segment_anchors.json")
    else:
        from tasks.phyts_tess.tools.stage_data import STAGED_FILENAME

        names = [STAGED_FILENAME.format(split=split) for split in ("train", "val")]
    missing_data = [
        str(settings.data_dir / name)
        for name in names
        if not (settings.data_dir / name).is_file()
    ]
    if missing_data:
        add(
            "Missing data files:\n    " + "\n    ".join(missing_data),
            "Follow this notebook's Data setup step: reuse the existing shared data on the 5090 host, "
            "or download/stage it locally once. Set data_dir in the saved experiment JSON; do not redownload existing large files.",
        )
    if shutil.which("nvidia-smi") is None:
        add(
            "nvidia-smi is unavailable; an NVIDIA CUDA GPU is required.",
            "Install/enable the NVIDIA driver, or enable GPU access in the container/job. "
            "Run nvidia-smi in the launching terminal. AMD and Intel GPUs are unsupported.",
        )
    if issues:
        details = "\n".join(
            f"{i}. {issue.problem}\n   Fix: {issue.fix}"
            for i, issue in enumerate(issues, 1)
        )
        raise ValueError(
            "Tutorial environment is not ready. No API call or training was started.\n"
            + details
        )
    print(
        "Setup files and required key names are present. Native source, data integrity and CUDA checks run before launch; key authentication is not yet verified.",
        flush=True,
    )


__all__ = ["SetupIssue", "require_ready", "shell_setup_guard"]
