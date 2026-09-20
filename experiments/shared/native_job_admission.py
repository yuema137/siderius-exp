"""Assemble one native validation job from protected captures and review evidence.

Called by the deployment coordinator after caller/source authentication. Scope
semantics remain a task-owned callback. No candidate source executes here.
"""

import hashlib
from collections.abc import Callable
from typing import Protocol

from agent.schemas.data_analysis.common import Sha256
from pydantic import BaseModel, ConfigDict

from experiments.shared.epoch_model_worker import EpochModelSource
from experiments.shared.native_loss_binding import (
    AdmittedLossSource,
    admitted_loss_source,
)
from experiments.shared.native_objective_metadata import NativeObjectiveMetadata
from experiments.shared.native_training_inputs import CapturedNativeInputs
from experiments.shared.native_training_metadata import (
    NativeConfigurationMetadata,
    NativeConfigurationRequest,
    captured_configuration_request,
)
from experiments.shared.objective_review_pipeline import AutomaticReviewBundle
from experiments.shared.validation_epoch_service import AdmittedValidationWorkload
from experiments.shared.validation_training_execution import (
    AdmittedEpochPlan,
    ReviewedEpochObjective,
)


class ConfigurationProbe(Protocol):
    def configuration(
        self, request: NativeConfigurationRequest
    ) -> NativeConfigurationMetadata: ...


class ScopeAdmission(Protocol):
    payload: str
    rows: int


class NativeReviewedObjective(BaseModel):
    """Operator-owned metadata/evidence and the protected worker bundle location."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    metadata: NativeObjectiveMetadata
    bundle: AutomaticReviewBundle
    worker: ReviewedEpochObjective


class AdmittedNativeJob(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    plan: AdmittedEpochPlan
    model_source: EpochModelSource
    loss_source: AdmittedLossSource | None


def admit_native_job(
    captured: CapturedNativeInputs,
    *,
    model_source: EpochModelSource,
    probe: ConfigurationProbe,
    admit_scope: Callable[[NativeConfigurationMetadata], ScopeAdmission],
    device: str,
    builtin_objective_sha256: Sha256,
    reviewed: NativeReviewedObjective | None = None,
    review_resolver: Callable[[NativeConfigurationMetadata], NativeReviewedObjective]
    | None = None,
) -> AdmittedNativeJob:
    """Resolve configuration once and derive epoch policy from actual native values.

    The operator supplies the resolved device and builtin implementation identity.
    No static optimizer-step count or new training-pool restriction is introduced.
    Review runs before this assembly and is never repeated in the epoch loop.
    """
    request, epoch_limit = captured_configuration_request(captured, source=model_source)
    metadata = probe.configuration(request)
    scope = admit_scope(metadata)
    loss_source = None
    worker = None
    if reviewed is not None and review_resolver is not None:
        raise ValueError("native review must have one operator authority")
    if metadata.loss.loss_type == "custom":
        if review_resolver is not None:
            reviewed = review_resolver(metadata)
        if reviewed is None:
            raise ValueError("custom native loss requires operator review evidence")
        loss_source = admitted_loss_source(
            reviewed.bundle,
            policy_sha256=reviewed.worker.policy_sha256,
            objective_sha256=reviewed.worker.objective_sha256,
        )
        objective = reviewed.metadata
        if (
            metadata.loss.loss_name != loss_source.loss_name
            or objective.loss_name != loss_source.loss_name
            or objective.source_sha256
            != hashlib.sha256(loss_source.source.encode()).hexdigest()
            or objective.effective_parameters != loss_source.parameters
            or objective.package_sha256
            != (loss_source.code_package.sha256 if loss_source.code_package else None)
        ):
            raise ValueError("review evidence differs from native-selected loss")
        # The metadata probe owns dtype interpretation; a manually supplied worker
        # dtype is not another authority for the same plugin declaration.
        worker = reviewed.worker.model_copy(
            update={"target_dtype": objective.target_dtype}
        )
        with worker.bundle.open("rb") as stream:
            payload = stream.read(4194305)
        if len(payload) > 4194304:
            raise ValueError("worker review file exceeds transport limit")
        if AutomaticReviewBundle.model_validate_json(payload) != reviewed.bundle:
            raise ValueError("worker review file differs from admitted evidence")
    elif reviewed is not None:
        raise ValueError("builtin native loss cannot consume custom review evidence")
    workload = AdmittedValidationWorkload(
        model_type=metadata.model.model_type,
        configuration=metadata.model.configuration,
        model_io=metadata.model_io,
        loss=metadata.loss,
        scope_payload=scope.payload,
        device=device,
        batch_size=metadata.training.batch_size,
        expected_rows=scope.rows,
        max_epochs=epoch_limit,
    )
    return AdmittedNativeJob(
        plan=AdmittedEpochPlan(
            workload=workload,
            model=metadata.model,
            builtin_objective_sha256=None if worker else builtin_objective_sha256,
            reviewed_objective=worker,
        ),
        model_source=model_source,
        loss_source=loss_source,
    )
