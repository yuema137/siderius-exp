"""Execute an admitted native job and its epoch validation transactions.

This is called by the protected deployment launcher after input/source admission
and objective review. It is not a research-facing authorization endpoint. The
operator supplies task bindings, worker confinement and a continuing deadline;
no objective review or environment installation occurs in the epoch loop.
"""

import select
import socket
import time
from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

from agent.schemas.data_analysis.common import Sha256
from execute_tools.observables import DynamicObservableEpoch
from execute_tools.task_data_path import TaskDataPath
from execute_tools.validation_execution import (
    ValidationDeployment,
    ValidationExecutionResult,
)
from pydantic import BaseModel, ConfigDict, model_validator

from experiments.shared.builtin_objective_worker import BuiltinObjectiveWorkerConfig
from experiments.shared.epoch_model_worker import (
    EpochModelSource,
    EpochModelSpecification,
    EpochModelWorkerConfig,
)
from experiments.shared.native_loss_binding import AdmittedLossSource
from experiments.shared.native_training_channel import launch_native_training_channel
from experiments.shared.reviewed_objective_worker import ObjectiveWorkerConfig
from experiments.shared.validation_epoch_execution import (
    ValidationProgressRelay,
    execute_admitted_epoch,
)
from experiments.shared.validation_epoch_protocol import (
    NativeValidationCancelled,
    ValidationEpochMetadata,
)
from experiments.shared.validation_epoch_service import (
    AdmittedValidationWorkload,
    EpochExecutor,
    serve_validation_epoch,
)
from experiments.shared.validation_worker_process import launch_validation_worker


class ReviewedEpochObjective(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    bundle: Path
    policy_sha256: Sha256
    objective_sha256: Sha256
    target_dtype: Literal["long", "float"]


class AdmittedEpochPlan(BaseModel):
    """Operator-resolved inputs, never populated from an epoch request."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    workload: AdmittedValidationWorkload
    model: EpochModelSpecification
    builtin_objective_sha256: Sha256 | None = None
    reviewed_objective: ReviewedEpochObjective | None = None

    @model_validator(mode="after")
    def consistent_native_inputs(self) -> Self:
        if (
            self.model.model_type != self.workload.model_type
            or self.model.configuration != self.workload.configuration
            or self.model.loss_type != self.workload.loss.loss_type
        ):
            raise ValueError("worker model differs from admitted native workload")
        custom = self.workload.loss.loss_type == "custom"
        if custom != (self.reviewed_objective is not None) or custom == (
            self.builtin_objective_sha256 is not None
        ):
            raise ValueError("objective worker differs from admitted native loss")
        return self


@dataclass(frozen=True)
class EpochWorkerRuntime:
    python: Path
    cwd: Path
    environment: Mapping[str, str]
    confinement_prefix: Sequence[str]
    diagnostics: Path
    deadline_epoch: float
    max_frame_bytes: int
    max_snapshot_bytes: int


@dataclass(frozen=True)
class EpochTiming:
    epoch: int
    model_startup: float
    loss_startup: float
    validation: float
    r3: float
    rows: int


class AdmittedEpochExecutor:
    """Connect numeric workers to the native estimator with operator-owned data.

    Use one instance and a unique protected diagnostics directory per native job.
    Keep observations and timings private. Worker launch configurations include
    reviewed source identities and must not be exposed to the research process.
    """

    def __init__(
        self,
        *,
        plan: AdmittedEpochPlan,
        runtime: EpochWorkerRuntime,
        data_path: TaskDataPath,
        data_dir: str,
        observables: DynamicObservableEpoch | None = None,
    ):
        self.plan = plan
        self.runtime = runtime
        self.data_path = data_path
        self.scope = data_path.deserialize_scope(plan.workload.scope_payload)
        self.data_dir = data_dir
        self.observables = observables
        self.timings: list[EpochTiming] = []

    def __call__(
        self,
        request: ValidationEpochMetadata,
        snapshots: tuple[int, int],
        progress: ValidationProgressRelay,
    ) -> ValidationExecutionResult:
        # Also guard direct callers before creating workers or reading samples.
        self.plan.workload.check(request, sequence=len(self.timings))
        runtime = self.runtime
        common = {
            "device": self.plan.workload.device,
            "deadline_epoch": runtime.deadline_epoch,
            "max_frame_bytes": runtime.max_frame_bytes,
        }
        model = EpochModelWorkerConfig(
            specification=self.plan.model,
            state_fd=snapshots[0],
            max_snapshot_bytes=runtime.max_snapshot_bytes,
            training=request.model_training,
            **common,
        )
        reviewed = self.plan.reviewed_objective
        if reviewed is not None:
            objective = ObjectiveWorkerConfig(
                bundle=reviewed.bundle,
                policy_sha256=reviewed.policy_sha256,
                objective_sha256=reviewed.objective_sha256,
                state_fd=snapshots[1],
                training=request.objective_training,
                **common,
            )
        else:
            assert self.plan.builtin_objective_sha256 is not None
            objective = BuiltinObjectiveWorkerConfig(
                loss=self.plan.workload.loss,
                source_sha256=self.plan.builtin_objective_sha256,
                state_fd=snapshots[1],
                max_snapshot_bytes=runtime.max_snapshot_bytes,
                training=request.objective_training,
                **common,
            )
        with ExitStack() as stack:
            workers = [
                stack.enter_context(
                    launch_validation_worker(
                        config,
                        python=runtime.python,
                        cwd=runtime.cwd,
                        config_path=runtime.diagnostics
                        / f"{request.sequence}-{role}.json",
                        stderr_path=runtime.diagnostics
                        / f"{request.sequence}-{role}.stderr",
                        environment=runtime.environment,
                        confinement_prefix=runtime.confinement_prefix,
                    )
                )
                for role, config in (("model", model), ("loss", objective))
            ]
            started = time.perf_counter()
            result = execute_admitted_epoch(
                request,
                model=workers[0].peer,
                objective=workers[1].peer,
                data_path=self.data_path,
                scope=self.scope,
                data_dir=self.data_dir,
                progress=progress,
                observables=self.observables,
                resolved_custom_target_dtype=(
                    reviewed.target_dtype if reviewed else None
                ),
            )
            timing = EpochTiming(
                epoch=request.sequence + 1,
                model_startup=workers[0].startup_seconds,
                loss_startup=workers[1].startup_seconds,
                validation=time.perf_counter() - started,
                r3=result.r3,
                rows=result.rows,
            )
        self.timings.append(timing)
        return result


@dataclass(frozen=True)
class NativeValidationRunResult:
    returncode: int
    validation_epochs: int
    elapsed_seconds: float


def run_admitted_native_training(
    command: Sequence[str],
    *,
    python: Path,
    entrypoint: Path,
    deployment: ValidationDeployment,
    environment: Mapping[str, str],
    confinement_prefix: Sequence[str],
    cwd: Path,
    workload: AdmittedValidationWorkload,
    execute: EpochExecutor,
    deadline: float,
    max_metadata_bytes: int,
    max_snapshot_bytes: int,
    entry_module: str | None = "experiments.shared.native_training_entry",
    model_source: EpochModelSource | None = None,
    loss_source: AdmittedLossSource | None = None,
) -> NativeValidationRunResult:
    """Serve until native exit, including early rejection, under one deadline.

    Preserve native stdout/stderr and exit status for the existing tuner. A clean
    exit without validation can be a native runtime rejection: the tuner still
    interprets its own result/sentinel files. Do not fabricate successful history.
    On failure the channel owner reaps the direct child; the deployment's outer
    watchdog/confinement must also clean descendants, as with normal training.
    """
    started = time.monotonic()
    if started >= deadline:
        raise TimeoutError("native validation run deadline exhausted before launch")
    sequence = 0
    with launch_native_training_channel(
        command,
        python=python,
        entrypoint=entrypoint,
        deployment=deployment,
        environment=environment,
        confinement_prefix=confinement_prefix,
        cwd=cwd,
        entry_module=entry_module,
        model_source=model_source,
        loss_source=loss_source,
    ) as job:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("native validation run deadline exhausted")
            ready, _, _ = select.select([job.channel], [], [], min(0.1, remaining))
            if ready:
                if not job.channel.recv(1, socket.MSG_PEEK):
                    # The child may close the channel just before process exit.
                    code = job.process.wait(
                        timeout=max(0.001, deadline - time.monotonic())
                    )
                    break
                try:
                    sequence = serve_validation_epoch(
                        job.channel,
                        workload=workload,
                        sequence=sequence,
                        execute=execute,
                        deadline=deadline,
                        max_metadata_bytes=max_metadata_bytes,
                        max_snapshot_bytes=max_snapshot_bytes,
                    )
                except NativeValidationCancelled:
                    code = job.process.wait(
                        timeout=max(0.001, deadline - time.monotonic())
                    )
                    break
            elif (code := job.process.poll()) is not None:
                break
    return NativeValidationRunResult(code, sequence, time.monotonic() - started)
