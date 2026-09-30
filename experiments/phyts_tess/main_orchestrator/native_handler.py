"""TESS adapter for the protected per-invocation native launcher.

The caller trains **through** SIDERIUS rather than around it. Its invocation
is captured, its model source and objective are admitted, its validation
scope is checked against the operator's frozen task, and only then does
training run — with per-epoch validation served by the evaluator, which owns
truth.

This is a port of `experiments/tidmad/main_orchestrator/native_handler.py`.
Every stage, ordering and confinement decision is that file's; what differs
is the task binding:

* scope admission checks the caller's request against the answer-free
  agent view, then REBUILDS the admitted scope from the evaluator's identity
  manifest so its rows carry targets — the per-epoch executor binds the
  truth-bearing `PhytsTessTaskDataPath`, as TIDMAD binds `TidmadTaskDataPath()`,
  and runs in the coordinator's process where the caller cannot see it;
* validation admission carries an agent view instead of a band and a
  segmentation size — TESS declares no partition vocabulary and fixes its
  window at 1024 in the forward contract;
* the row declaration is this task's.

**What is verified, and what is not.** The shared machinery it calls exists
with these signatures, the policy validates, and the admission closure is
exercised in tests. Execution is **not** verified: it needs a deployed
launcher, its namespaces and a protected runner, none of which exist for
TESS yet. `prepare.py` records that as a launch blocker rather than letting
the port read as a working deployment.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, replace
from pathlib import Path

from agent.schemas.data_analysis.common import Sha256
from execute_tools.dataset_config import DatasetProfile, bind_dataset_profile
from execute_tools.training_cli import build_training_parser
from execute_tools.validation_execution import ValidationDeployment
from pydantic import BaseModel, ConfigDict, Field

from experiments.phyts_tess.main_orchestrator.public_data_path import (
    PUBLIC_TESS_TASK_ID,
)
from experiments.phyts_tess.main_orchestrator.validation_scope import (
    admit_captured_validation_scope,
)
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
from tasks.phyts_tess.runtime.tess_data_path import PhytsTessTaskDataPath

__all__ = ["ROW_DECLARATION", "TessNativePolicy", "run", "run_with_policy"]

#: Where the validation client finds this task's workload declaration.
ROW_DECLARATION = (
    "experiments.phyts_tess.main_orchestrator.validation_rows:declared_rows"
)

_MAX_CAPTURED_FILE_BYTES = 4194304


class TessNativePolicy(BaseModel):
    """What the deployment fixes before the caller is allowed to invoke."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime: NativeRuntimePolicy
    manifest: Path
    manifest_sha256: Sha256
    profile: DatasetProfile
    #: The caller's answer-free view. Scope admission checks the caller's
    #: request against the operator's copy of it, never against whatever the
    #: caller supplies.
    agent_view: Path
    #: The evaluator's identity manifest, which carries the validation
    #: targets. Per-epoch validation loss is computed against THIS, on the
    #: coordinator's side; the caller's view has no target to compute against.
    truth_manifest: Path
    truth_manifest_sha256: Sha256
    #: Where the light curves live. Flux is input, not an answer.
    validation_data: Path
    task_data_path_id: str = Field(default=PUBLIC_TESS_TASK_ID, min_length=1)
    review: NativeReviewPolicy | None = None


def run(context: NativeLaunchContext, command: tuple[str, ...]) -> int:
    return run_with_policy(
        context, command, TessNativePolicy.model_validate(context.policy.settings)
    )


def run_with_policy(
    context: NativeLaunchContext,
    command: tuple[str, ...],
    policy: TessNativePolicy,
    *,
    gateway: ReviewGateway | None = None,
) -> int:
    """Execute after caller authorization; the gateway is a test injection."""
    runtime = policy.runtime
    started = time.monotonic()
    timings: dict[str, float] = {}
    if time.monotonic() >= context.deadline:
        raise TimeoutError("native run deadline exhausted before capture")
    # The manifest per-epoch validation is computed against is pinned by
    # digest, exactly as the composition manifest is: a swapped or edited
    # truth file must refuse the run, not quietly change every loss it reports.
    observed = hashlib.sha256(policy.truth_manifest.read_bytes()).hexdigest()
    if observed != policy.truth_manifest_sha256:
        raise ValueError(
            "evaluator identity manifest changed after the policy was drafted"
        )

    job = Path(tempfile.mkdtemp(prefix="native-job-", dir=runtime.job_parent))
    captured = capture_native_training_inputs(
        command,
        python=runtime.python,
        entrypoint=runtime.entrypoint,
        source_cwd=context.source_cwd,
        allowed_roots=runtime.readable_roots,
        parent=job,
        owner_uid=os.geteuid(),
        max_file_bytes=_MAX_CAPTURED_FILE_BYTES,
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
    # Configuration resolution reads the operator-captured model code, not
    # the mutable roots the caller used for discovery.
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
        # `metadata` carries the caller's model configuration. TESS reads
        # nothing from it: its window is fixed by the forward contract, so
        # there is no per-model geometry to reconcile.
        del metadata
        return admit_captured_validation_scope(
            captured,
            manifest=policy.manifest,
            manifest_sha256=policy.manifest_sha256,
            source_cwd=context.source_cwd,
            agent_view=policy.agent_view,
            truth_manifest=policy.truth_manifest,
            task_data_path_id=policy.task_data_path_id,
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

    # The truth-bearing pack data path, as TIDMAD binds `TidmadTaskDataPath()`:
    # the admitted scope carries the evaluator's targets, and this executor
    # runs in the coordinator's own process, never in the caller's.
    adapter = PhytsTessTaskDataPath(manifest_path=str(policy.truth_manifest))
    execute = AdmittedEpochExecutor(
        plan=admitted.plan,
        runtime=worker_runtime,
        data_path=adapter,
        data_dir=str(policy.validation_data),
    )
    deployment = ValidationDeployment(
        factory=(
            "experiments.shared.validation_client_factory:create_validation_client"
        ),
        settings={
            "row_declaration": ROW_DECLARATION,
            "deadline_epoch": time.time()
            + max(0.0, context.deadline - time.monotonic()),
            "max_metadata_bytes": runtime.max_metadata_bytes,
            "max_state_bytes": runtime.max_snapshot_bytes,
        },
    )

    # Preserve what the caller's relative paths meant before the privileged
    # cwd moved out from under them.
    args = build_training_parser().parse_args(captured.command[2:])
    argv = list(captured.command)
    for name in ("data_dir", "sandbox_dir", "runtime_observation_out"):
        value = getattr(args, name, None)
        if value:
            path = Path(value)
            argv.extend(
                (
                    f"--{name}",
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
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    path.chmod(0o600)
    return result.returncode
