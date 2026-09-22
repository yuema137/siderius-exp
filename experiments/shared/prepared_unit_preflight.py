"""Qualification-independent launch identity for prepared regression units."""

from __future__ import annotations

import hashlib
import pwd
import subprocess
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from workflows.task_composition import compose_run_task_bindings

from experiments.shared.checksum_manifest import sha256_file
from experiments.shared.framework_pin import (
    verify_framework_pin,
    verify_installed_framework,
)
from experiments.shared.prepared_workflow_command import build_command
from experiments.shared.workflow_credentials import required_workflow_api_keys


class UnitDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["prepared-fixed-unit-v1"]
    campaign_seconds: int = Field(gt=0)
    gpu_name: str = Field(min_length=1)


class ArrayEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ManifestEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    artifacts: tuple[ArrayEvidence, ...] = Field(min_length=1)


class PreparedPreflight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    command: tuple[str, ...] = Field(min_length=1)
    campaign_seconds: int = Field(gt=0)
    infra_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    exp_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    composition_fingerprint: str
    data: dict[str, JsonValue]
    runner: str
    runner_uid: int = Field(gt=0)
    runner_gid: int = Field(ge=0)
    runner_home: str
    gpu: str
    required_api_keys: tuple[str, ...]


def verify_prepared_arrays(data: Path, expected_manifest: str) -> dict[str, object]:
    raw = (data / "manifest.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_manifest:
        raise ValueError("prepared manifest differs from the pinned task declaration")
    manifest = ManifestEvidence.model_validate_json(raw)
    required = {
        "training/inputs.npy",
        "training/targets.npy",
        "evaluator/validation/inputs.npy",
        "evaluator/validation/targets.npy",
        "evaluator/validation/loss_indices.npy",
    }
    if {artifact.path for artifact in manifest.artifacts} != required or len(
        manifest.artifacts
    ) != len(required):
        raise ValueError("prepared manifest must name exactly the five declared arrays")
    for artifact in manifest.artifacts:
        relative = PurePosixPath(artifact.path)
        path = data / relative
        if relative.is_absolute() or ".." in relative.parts or path.is_symlink():
            raise ValueError("prepared array must be a contained regular file")
        if path.stat().st_mode & 0o222 or path.stat().st_size != artifact.bytes:
            raise ValueError(
                f"prepared array is writable or has the wrong size: {relative}"
            )
        if sha256_file(path) != artifact.sha256:
            raise ValueError(f"prepared array checksum mismatch: {relative}")
    return {
        "manifest_sha256": expected_manifest,
        "arrays": [a.model_dump() for a in manifest.artifacts],
    }


def resolve_preflight(
    *,
    experiment: Path,
    checkout: Path,
    data: Path,
    unit: Path,
    run_name: str,
    runner: str,
) -> PreparedPreflight:
    root = Path(__file__).resolve().parents[2]
    revision = verify_framework_pin(root, checkout)
    verify_installed_framework(revision, root)
    definition = UnitDefinition.model_validate_json(
        (experiment / "unit.json").read_bytes()
    )
    command = build_command(
        experiment=experiment,
        checkout=checkout,
        data=data,
        workspace=unit / "workspace",
        run_name=run_name,
        qualification=False,
    )
    account = pwd.getpwnam(runner)
    if account.pw_uid == 0:
        raise ValueError("the workflow must run as a dedicated non-root account")
    gpu = subprocess.run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if len(gpu) != 1 or definition.gpu_name not in gpu[0]:
        raise ValueError(f"expected one {definition.gpu_name}; observed {gpu}")
    composition_path = Path(command[command.index("--task_composition") + 1])
    composition = compose_run_task_bindings(str(composition_path))
    data_receipt = verify_prepared_arrays(
        data, composition.task_data_path.declaration.manifest_sha256
    )
    exp_revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return PreparedPreflight.model_validate(
        {
            "command": command,
            "campaign_seconds": definition.campaign_seconds,
            "infra_revision": revision,
            "exp_revision": exp_revision,
            "composition_fingerprint": composition.semantic_fingerprint,
            "data": data_receipt,
            "runner": runner,
            "runner_uid": account.pw_uid,
            "runner_gid": account.pw_gid,
            "runner_home": account.pw_dir,
            "gpu": gpu[0],
            "required_api_keys": sorted(
                required_workflow_api_keys(
                    experiment / "agents.json",
                    disabled_roles=frozenset({"data_analysis"}),
                )
            ),
        }
    )
