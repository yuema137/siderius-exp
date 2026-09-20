"""Concrete TIDMAD adapter for the protected per-invocation native launcher."""

import json
import os
import tempfile
import time
from dataclasses import asdict, replace
from pathlib import Path

from agent.schemas.data_analysis.common import Sha256
from execute_tools.dataset_config import DataScope, DatasetProfile, bind_dataset_profile
from execute_tools.training_cli import build_training_parser
from execute_tools.validation_execution import ValidationDeployment
from pydantic import BaseModel, ConfigDict, Field

from experiments.shared.native_job_admission import admit_native_job
from experiments.shared.native_launcher import NativeLaunchContext
from experiments.shared.native_runtime import (
    NativeRuntimePolicy,
    admit_model_source,
    inherited_package,
)
from experiments.shared.native_runtime_review import (
    NativeReviewPolicy,
    review_selected_native_loss,
)
from experiments.shared.native_training_inputs import capture_native_training_inputs
from experiments.shared.objective_purpose_review import ReviewGateway
from experiments.shared.validation_admission_process import AdmissionProbeRuntime
from experiments.shared.validation_confinement import NamespaceMount
from experiments.shared.validation_training_execution import (
    AdmittedEpochExecutor,
    EpochWorkerRuntime,
    run_admitted_native_training,
)
from experiments.tidmad.main_orchestrator.validation_scope import (
    admit_captured_validation_scope,
)
from tasks.tidmad.runtime.tidmad_data_path import TidmadTaskDataPath


class TidmadNativePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    runtime: NativeRuntimePolicy
    manifest: Path
    manifest_sha256: Sha256
    task_data_path_id: str = Field(min_length=1)
    profile: DatasetProfile
    allowed_scope: DataScope
    validation_data: Path
    review: NativeReviewPolicy | None = None


def run(context: NativeLaunchContext, command: tuple[str, ...]) -> int:
    return run_with_policy(
        context, command, TidmadNativePolicy.model_validate(context.policy.settings)
    )


def run_with_policy(
    context: NativeLaunchContext,
    command: tuple[str, ...],
    policy: TidmadNativePolicy,
    *,
    gateway: ReviewGateway | None = None,
) -> int:
    """Execute after caller authorization; optional gateway is a test injection."""
    runtime = policy.runtime
    started = time.monotonic()
    timings = {}
    if time.monotonic() >= context.deadline:
        raise TimeoutError("native run deadline exhausted before capture")
    job = Path(tempfile.mkdtemp(prefix="native-job-", dir=runtime.job_parent))
    captured = capture_native_training_inputs(
        command,
        python=runtime.python,
        entrypoint=runtime.entrypoint,
        source_cwd=context.source_cwd,
        allowed_roots=runtime.readable_roots,
        parent=job,
        owner_uid=os.geteuid(),
        max_file_bytes=4194304,
    )
    package = inherited_package(context, runtime)
    timings["input_capture"] = time.monotonic() - started
    stage_started = time.monotonic()
    probe = AdmissionProbeRuntime(
        python=runtime.python,
        namespace=runtime.probe_namespace,
        environment={**runtime.child_environment, **context.source_environment},
        diagnostics=job,
        deadline=context.deadline,
    )
    source = admit_model_source(context, runtime, captured, probe, package, job)
    timings["model_selection_capture"] = time.monotonic() - stage_started
    mounts = [NamespaceMount(source=captured.root, target=captured.root)]
    if source.plugin_package is not None:
        mounts.append(
            NamespaceMount(
                source=source.plugin_package.root, target=source.plugin_package.root
            )
        )
    # Configuration resolution uses operator-captured model code, not the mutable
    # original roots used for initial native discovery.
    probe = replace(
        probe,
        namespace=probe.namespace.model_copy(
            update={"mounts": (*probe.namespace.mounts, *mounts)}
        ),
    )
    reviewed = None

    def resolve_review(metadata):
        nonlocal reviewed
        review_started = time.monotonic()
        if policy.review is None:
            raise ValueError("custom loss review policy is missing from deployment")
        reviewed = review_selected_native_loss(
            metadata.loss.loss_name,
            context=context,
            runtime=runtime,
            policy=policy.review,
            probe=probe,
            package=package,
            job=job,
            gateway=gateway,
        )
        timings["objective_selection_and_review"] = time.monotonic() - review_started
        return reviewed

    def admit_scope(metadata):
        return admit_captured_validation_scope(
            captured,
            manifest=policy.manifest,
            manifest_sha256=policy.manifest_sha256,
            task_data_path_id=policy.task_data_path_id,
            source_cwd=context.source_cwd,
            profile=policy.profile,
            allowed_scope=policy.allowed_scope,
            model_segmentation_size=metadata.model.configuration["segmentation_size"],
        )

    stage_started = time.monotonic()
    admitted = admit_native_job(
        captured,
        model_source=source,
        probe=probe,
        admit_scope=admit_scope,
        device=runtime.device,
        builtin_objective_sha256=runtime.builtin_objective_sha256,
        review_resolver=resolve_review,
    )
    timings["configuration_scope_and_review"] = time.monotonic() - stage_started
    native_namespace = runtime.training_namespace.model_copy(
        update={"mounts": (*runtime.training_namespace.mounts, *mounts)}
    )
    worker_mounts = [mount for mount in mounts if mount.source != captured.root]
    if reviewed is not None:
        worker_mounts.append(
            NamespaceMount(source=reviewed.worker.bundle, target=reviewed.worker.bundle)
        )
    worker_namespace = runtime.worker_namespace.model_copy(
        update={"mounts": (*runtime.worker_namespace.mounts, *worker_mounts)}
    )
    worker_runtime = EpochWorkerRuntime(
        python=runtime.python,
        cwd=context.policy.cwd,
        environment=runtime.child_environment,
        confinement_prefix=worker_namespace.prefix(),
        diagnostics=job,
        deadline_epoch=time.time() + max(0.0, context.deadline - time.monotonic()),
        max_frame_bytes=runtime.max_snapshot_bytes,
        max_snapshot_bytes=runtime.max_snapshot_bytes,
    )
    adapter = TidmadTaskDataPath()
    execute = AdmittedEpochExecutor(
        plan=admitted.plan,
        runtime=worker_runtime,
        data_path=adapter,
        data_dir=str(policy.validation_data),
    )
    deployment = ValidationDeployment(
        factory="experiments.shared.validation_client_factory:create_validation_client",
        settings={
            "row_declaration": "experiments.tidmad.main_orchestrator.validation_rows:declared_rows",
            "deadline_epoch": time.time()
            + max(0.0, context.deadline - time.monotonic()),
            "max_metadata_bytes": runtime.max_metadata_bytes,
            "max_state_bytes": runtime.max_snapshot_bytes,
        },
    )
    # Preserve original relative-path meaning after moving the privileged cwd.
    args = build_training_parser().parse_args(captured.command[2:])
    argv = list(captured.command)
    for name in ("data_dir", "sandbox_dir", "runtime_observation_out"):
        value = getattr(args, name, None)
        if value:
            path = Path(value)
            argv.extend(
                (
                    "--" + name,
                    str(path if path.is_absolute() else context.source_cwd / path),
                )
            )
    with bind_dataset_profile(policy.profile):
        result = run_admitted_native_training(
            argv,
            python=runtime.python,
            entrypoint=runtime.entrypoint,
            deployment=deployment,
            environment=runtime.child_environment,
            confinement_prefix=native_namespace.prefix(),
            cwd=context.policy.cwd,
            workload=admitted.plan.workload,
            execute=execute,
            deadline=context.deadline,
            max_metadata_bytes=runtime.max_metadata_bytes,
            max_snapshot_bytes=runtime.max_snapshot_bytes,
            model_source=admitted.model_source,
            loss_source=admitted.loss_source,
        )
    timings["total"] = time.monotonic() - started
    receipt = {
        "stages_seconds": timings,
        "result": asdict(result),
        "epochs": [asdict(timing) for timing in execute.timings],
    }
    path = job / "execution.json"
    path.write_text(json.dumps(receipt, indent=2))
    path.chmod(0o600)
    return result.returncode
