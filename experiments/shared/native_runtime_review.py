"""Resolve and review the native-selected custom loss once before training."""

import os
import time
from pathlib import Path

from agent.schemas.data_analysis.common import Sha256
from core.local_code import CapturedCodePackage
from pydantic import BaseModel, ConfigDict

from experiments.shared.native_job_admission import NativeReviewedObjective
from experiments.shared.native_launcher import NativeLaunchContext
from experiments.shared.native_loss_discovery import LossDiscoveryRequest
from experiments.shared.native_objective_metadata import ObjectiveMetadataRequest
from experiments.shared.native_runtime import NativeRuntimePolicy
from experiments.shared.native_source_capture import capture_selected_source
from experiments.shared.objective_code_package import ObjectiveCodePackage
from experiments.shared.objective_numerical_review import (
    NumericalReviewRequest,
    SyntheticTensor,
)
from experiments.shared.objective_purpose_review import (
    ObjectiveReviewMaterial,
    ReviewGateway,
)
from experiments.shared.validation_admission import review_native_objective_once
from experiments.shared.validation_admission_process import AdmissionProbeRuntime
from experiments.shared.validation_training_execution import ReviewedEpochObjective


class NativeReviewPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    registry: Path
    run_id: str
    policy_sha256: Sha256
    allowed_import_roots: tuple[str, ...]
    dependency_declaration: str
    provider: str
    model_id: str
    reasoning_effort: str | None = None
    credential_file: Path
    credential_key: str
    float_prediction: SyntheticTensor
    float_target: SyntheticTensor
    long_prediction: SyntheticTensor
    long_target: SyntheticTensor


def native_review_gateway(policy: NativeReviewPolicy, deadline: float) -> ReviewGateway:
    from agent.llm_bridge import LLMBridge
    from dotenv import dotenv_values

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("native review deadline exhausted")
    key = dotenv_values(policy.credential_file).get(policy.credential_key)
    if not key:
        raise ValueError("native review credential is unavailable")
    return LLMBridge(
        provider=policy.provider,
        model_id=policy.model_id,
        reasoning_effort=policy.reasoning_effort,
        api_key=key,
        request_timeout=min(120.0, remaining),
        max_retries=0,
        timeout_retries=0,
    )


def review_selected_native_loss(
    name: str,
    *,
    context: NativeLaunchContext,
    runtime: NativeRuntimePolicy,
    policy: NativeReviewPolicy,
    probe: AdmissionProbeRuntime,
    package: CapturedCodePackage | None,
    job: Path,
    gateway: ReviewGateway | None = None,
) -> NativeReviewedObjective:
    selection = probe.loss_selection(LossDiscoveryRequest(loss_name=name))
    if selection.loss_name != name:
        raise ValueError("native selected loss differs from requested configuration")
    code_package = None
    if package is not None:
        member = package.member(selection.plugin_path)
        if member is None or member.pin.content_sha256 != selection.source_sha256:
            raise ValueError("selected loss differs from inherited package")
        source = member.source.decode()
        code_package = ObjectiveCodePackage(
            entrypoint=member.pin.member,
            sources={item.pin.member: item.source.decode() for item in package.members},
        )
    else:
        source = capture_selected_source(
            selection.plugin_path,
            expected_sha256=selection.source_sha256,
            allowed_roots=runtime.readable_roots,
            source_cwd=context.source_cwd,
        )
    metadata = probe.objective_metadata(
        ObjectiveMetadataRequest(
            source=source, loss_name=name, code_package=code_package
        )
    )
    prediction, target = (
        (policy.long_prediction, policy.long_target)
        if metadata.target_dtype == "long"
        else (policy.float_prediction, policy.float_target)
    )
    numerical = NumericalReviewRequest(
        source=source,
        loss_name=name,
        parameters=metadata.effective_parameters,
        prediction=prediction,
        target=target,
        code_package=code_package,
    )
    material = ObjectiveReviewMaterial(
        sources=code_package.sources if code_package else {"loss.py": source},
        effective_parameters=metadata.effective_parameters,
        dependency_declaration=policy.dependency_declaration,
    )
    bundle = review_native_objective_once(
        material,
        numerical,
        metadata,
        registry=policy.registry,
        owner_uid=os.geteuid(),
        run_id=policy.run_id,
        policy_sha256=policy.policy_sha256,
        allowed_import_roots=frozenset(policy.allowed_import_roots),
        numerical_worker=probe.numerical,
        gateway=gateway
        if gateway is not None
        else native_review_gateway(policy, context.deadline),
        deadline=context.deadline,
    )
    if bundle.receipt.decision != "approved":
        raise ValueError(
            "custom native loss was refused; see protected review evidence"
        )
    path = job / "objective-review.json"
    path.write_text(bundle.model_dump_json())
    path.chmod(
        0o444
    )  # Parent stays private; only mount this file into the numeric worker.
    return NativeReviewedObjective(
        metadata=metadata,
        bundle=bundle,
        worker=ReviewedEpochObjective(
            bundle=path,
            policy_sha256=policy.policy_sha256,
            objective_sha256=bundle.material.sha256,
            target_dtype=metadata.target_dtype,
        ),
    )
