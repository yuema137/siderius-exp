"""Local input identity for reusing a paper notebook's completed script run.

This is a cache binding, not scientific provenance or a raw-data integrity check.
It covers the standard initialized tutorial package layout and fixed runners.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tutorials.paper.runner import ROOT, TutorialExperiment

Task = Literal["tess", "tidmad", "project8", "ligo"]


class DemoCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["paper-demo-completion-v2"] = "paper-demo-completion-v2"
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    experiment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inputs_unchanged: bool
    exit_code: int
    elapsed_seconds: float = Field(ge=0, allow_inf_nan=False)
    workspace: Path
    log: Path


def read_settings(experiment: Path, task: Task) -> TutorialExperiment:
    if task in ("project8", "ligo"):
        from tutorials.paper.prepared.runner import PreparedExperiment

        settings = PreparedExperiment.model_validate_json(experiment.read_text())
        if settings.task != task:
            raise ValueError("selected task and saved experiment disagree")
        return settings
    if task == "tidmad":
        from tutorials.paper.tidmad.runner import TidmadExperiment

        return TidmadExperiment.model_validate_json(experiment.read_text())
    return TutorialExperiment.model_validate_json(experiment.read_text())


def _source_identity(checkout: Path) -> tuple[str, str]:
    """Bind Git revision and tracked edits without reading credentials or caches."""
    command = ["git", "-C", str(checkout)]
    revision = subprocess.check_output([*command, "rev-parse", "HEAD"]).decode().strip()
    diff = subprocess.check_output(
        [*command, "diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--"]
    )
    return revision, hashlib.sha256(diff).hexdigest()


def input_identity(
    experiment: Path, script: Path, settings: TutorialExperiment, *, task: Task
) -> str:
    """Hash declared local inputs; never read raw data or execute task plugins."""
    if settings.composition is None or settings.llm_config is None:
        raise ValueError("select saved composition and llm_config paths")
    if task in ("project8", "ligo"):
        from tutorials.paper.prepared.runner import workflow_files

        workflow, treatment = workflow_files(settings)
        extra = [settings.literature_config]
        trees = [settings.composition.parent.parent.parent / "shared"]
    elif task == "tidmad":
        from tutorials.paper.tidmad.runner import workflow_files

        workflow, treatment = workflow_files()
        extra, trees = [], []  # Literature settings are inside the selected task.
    else:
        from tutorials.paper.runner import workflow_files

        workflow, treatment = workflow_files()
        extra, trees = [], []
    paths = [experiment, script, settings.composition, settings.llm_config]
    paths.extend([workflow, treatment, *extra])
    trees.append(settings.composition.parent.parent)
    for tree in trees:
        if not tree.is_dir():
            raise ValueError(f"missing tutorial task directory: {tree}")
        paths.extend(
            p
            for p in tree.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        # Include both the selected name and resolved target, including file symlinks.
        digest.update(str(path.absolute()).encode() + b"\0")
        digest.update(str(path.resolve()).encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    sources = {
        str(p.resolve()): _source_identity(p) for p in (ROOT, settings.infra_checkout)
    }
    digest.update(json.dumps(sources, sort_keys=True).encode())
    return digest.hexdigest()
