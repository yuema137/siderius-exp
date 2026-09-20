"""Operator policy and source admission shared by concrete native task runners."""

import json
import os
from pathlib import Path

from agent.schemas.data_analysis.common import Sha256
from core.local_code import CapturedCodePackage, MemberIdentity
from pydantic import BaseModel, ConfigDict, Field

from experiments.shared.epoch_model_worker import EpochModelSource, StagedModelPackage
from experiments.shared.native_launcher import NativeLaunchContext
from experiments.shared.native_model_discovery import ModelDiscoveryRequest
from experiments.shared.native_source_capture import (
    capture_native_code_transport,
    capture_selected_source,
)
from experiments.shared.native_training_inputs import CapturedNativeInputs
from experiments.shared.validation_admission_process import AdmissionProbeRuntime
from experiments.shared.validation_code_snapshot import stage_validation_code
from experiments.shared.validation_confinement import ValidationNamespace


class NativeRuntimePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    python: Path
    entrypoint: Path
    readable_roots: tuple[Path, ...]
    job_parent: Path
    probe_namespace: ValidationNamespace
    training_namespace: ValidationNamespace
    worker_namespace: ValidationNamespace
    child_environment: dict[str, str]
    device: str = Field(pattern=r"^(cpu|cuda:[0-9]+)$")
    constructor_sha256: Sha256
    builtin_model_sha256: Sha256
    builtin_objective_sha256: Sha256
    max_snapshot_bytes: int = Field(gt=0)
    max_metadata_bytes: int = Field(default=1048576, gt=0)


def captured_json(captured: CapturedNativeInputs, name: str):
    """Read the operator's own captured input, not the research-side original."""
    item = next(item for item in captured.files if item.argument == name)
    return json.loads(item.captured.read_bytes())


def inherited_package(
    context: NativeLaunchContext, policy: NativeRuntimePolicy
) -> CapturedCodePackage | None:
    source = context.source_environment
    manifest = source.get("SIDERIUS_TASK_CODE_MANIFEST")
    digest = source.get("SIDERIUS_TASK_CODE_SHA256")
    if bool(manifest) != bool(digest):
        raise ValueError("native package transport is incomplete")
    if not manifest:
        return None
    return capture_native_code_transport(
        Path(manifest),
        manifest_sha256=digest,
        allowed_roots=policy.readable_roots,
        source_cwd=context.source_cwd,
    )


def admit_model_source(
    context: NativeLaunchContext,
    policy: NativeRuntimePolicy,
    captured: CapturedNativeInputs,
    probe: AdmissionProbeRuntime,
    package: CapturedCodePackage | None,
    job: Path,
) -> EpochModelSource:
    name = captured_json(captured, "model_cfg")["model_type"]
    selection = probe.model_selection(ModelDiscoveryRequest(model_type=name))
    if selection.constructor_sha256 != policy.constructor_sha256:
        raise ValueError("native constructor differs from deployed runtime")
    if selection.model_type != name:
        raise ValueError("native model selection differs from requested configuration")
    common = {
        "model_type": name,
        "constructor_sha256": policy.constructor_sha256,
        "source_sha256": selection.source_sha256,
    }
    if selection.plugin_path is None:
        if selection.source_sha256 != policy.builtin_model_sha256:
            raise ValueError("builtin native model differs from deployed runtime")
        return EpochModelSource(**common)
    if package is not None:
        member = package.member(selection.plugin_path)
        if member is None or member.pin.content_sha256 != selection.source_sha256:
            raise ValueError("selected model differs from inherited package")
        staged = stage_validation_code(package, parent=job, owner_uid=os.geteuid())
        return EpochModelSource(
            **common,
            plugin_package=StagedModelPackage(
                root=staged.root,
                identity=MemberIdentity(
                    package=staged.identity, member=member.pin.member
                ),
            ),
        )
    source = capture_selected_source(
        selection.plugin_path,
        expected_sha256=selection.source_sha256,
        allowed_roots=policy.readable_roots,
        source_cwd=context.source_cwd,
        max_bytes=4194304,
    )
    return EpochModelSource(**common, plugin_source=source)
