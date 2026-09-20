"""Resolve loss requests against deployment-owned training completions.

This reader does not issue completions, execute models or grant data access.
The deployment must provision the registry in a protected parent and permit
only its trusted training supervisor to publish completed native executions.
Research-side artifact manifests must never be copied here as authorization.
"""

from __future__ import annotations

import fcntl
import os
import stat
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal

from agent.schemas.data_analysis.common import (
    CertifiedArtifactRef,
    NonEmptyStr,
    Sha256,
)
from agent.schemas.data_analysis.trained_model import TrainedModelArtifactRef
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from experiments.shared.native_objective_metadata import NativeObjectiveMetadata
from experiments.shared.objective_numerical_review import (
    NumericalReviewRequest,
    NumericalReviewResult,
)
from experiments.shared.objective_purpose_review import (
    ObjectiveReviewMaterial,
    ReviewGateway,
)
from experiments.shared.objective_review import ObjectiveReviewReceipt
from experiments.shared.objective_review_pipeline import AutomaticReviewBundle

RecordId = Annotated[
    str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}$")
]


class ValidationLossRequest(BaseModel):
    """No caller-selected model path, loss, data scope or executable payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    training_record_id: RecordId


class NativeTrainingCompletion(BaseModel):
    """Supervisor-issued authority, not a self-certified model descriptor."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    training_record_id: RecordId
    run_id: NonEmptyStr
    state: Literal["completed"]
    completed_epochs: Annotated[int, Field(strict=True, gt=0)]
    infra_revision: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
    task_composition_fingerprint: Sha256
    model: TrainedModelArtifactRef
    objective: CertifiedArtifactRef
    objective_review_id: RecordId
    validation_scope: CertifiedArtifactRef


def _require_owned(info: os.stat_result, owner_uid: int, *, directory: bool) -> None:
    kind_ok = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not kind_ok or info.st_uid != owner_uid or info.st_mode & 0o022:
        raise PermissionError("training registry must be owner-controlled")
    if not directory and info.st_nlink != 1:
        raise PermissionError("training completion must not be a hard link")


def _read_record(
    directory_fd: int, filename: str, owner_uid: int, *, limit: int = 65536
) -> bytes:
    fd = os.open(
        filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd
    )
    with os.fdopen(fd, "rb") as stream:
        _require_owned(os.fstat(stream.fileno()), owner_uid, directory=False)
        payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("admission record exceeds the metadata limit")
    return payload


def admit_validation_loss(
    request: ValidationLossRequest,
    *,
    registry: Path,
    owner_uid: int,
    run_id: str,
    infra_revision: str,
    task_composition_fingerprint: str,
    review_policy_sha256: str,
) -> NativeTrainingCompletion:
    """Read one immutable authority without executing caller-supplied code.

    Registry location, owner and active identities come from the trusted worker
    configuration, never the request. Keep the registry parent protected too.
    Artifact hashes still need verification before the admitted model is used.
    """
    request = ValidationLossRequest.model_validate(request)
    directory_fd = os.open(registry, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        _require_owned(os.fstat(directory_fd), owner_uid, directory=True)
        completion = NativeTrainingCompletion.model_validate_json(
            _read_record(directory_fd, f"{request.training_record_id}.json", owner_uid)
        )
        review = ObjectiveReviewReceipt.model_validate_json(
            _read_record(
                directory_fd, f"{completion.objective_review_id}.review.json", owner_uid
            )
        )
    finally:
        os.close(directory_fd)
    if (
        completion.training_record_id != request.training_record_id
        or completion.run_id != run_id
        or completion.infra_revision != infra_revision
        or completion.task_composition_fingerprint != task_composition_fingerprint
    ):
        raise ValueError("training completion does not belong to this execution")
    if (
        review.review_id != completion.objective_review_id
        or review.run_id != run_id
        or review.objective != completion.objective
        or review.policy_sha256 != review_policy_sha256
        or review.decision != "approved"
    ):
        raise ValueError("objective lacks a matching approved automatic review")
    return completion


def _acquire_review_lock(descriptor: int, deadline: float | None) -> None:
    """A concurrent review must not wait beyond the invocation's deadline."""
    if deadline is None:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        return
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("review lock deadline exhausted")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            time.sleep(min(0.02, remaining))


def publish_automatic_review(
    bundle: AutomaticReviewBundle,
    *,
    registry: Path,
    owner_uid: int,
    deadline: float | None = None,
) -> None:
    """Persist trusted review evidence before exposing its admission receipt.

    Only the deployment review coordinator calls this; never accept a bundle
    from the research process. A protected parent remains a deployment condition.
    Writers serialize briefly on the directory; readers see complete records.
    Existing identical publications are harmless; conflicting IDs are refused.
    This issues no training completion and grants no private data access.
    """
    bundle = AutomaticReviewBundle.model_validate_json(bundle.model_dump_json())
    records = (
        (
            f"{bundle.receipt.review_id}.evidence.json",
            bundle.model_dump_json().encode(),
            4194304,
        ),
        (
            f"{bundle.receipt.review_id}.review.json",
            bundle.receipt.model_dump_json().encode(),
            65536,
        ),
    )
    if any(len(payload) > limit for _, payload, limit in records):
        raise ValueError("review publication exceeds record limit")
    directory_fd = os.open(registry, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        _require_owned(os.fstat(directory_fd), owner_uid, directory=True)
        if os.geteuid() != owner_uid:
            raise PermissionError("review publisher must be the registry owner")
        _acquire_review_lock(directory_fd, deadline)
        pending = []
        # Check all conflicts before writing anything. Evidence comes first;
        # a crash cannot leave an approval with no complete evidence file.
        for name, payload, limit in records:
            try:
                old = _read_record(directory_fd, name, owner_uid, limit=limit)
            except FileNotFoundError:
                pending.append((name, payload))
            else:
                if old != payload:
                    raise FileExistsError(
                        "review ID already identifies different evidence"
                    )
        for name, payload in pending:
            temporary = f".review-{uuid.uuid4().hex}.tmp"
            fd = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=directory_fd,
            )
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.rename(
                    temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd
                )
                os.fsync(directory_fd)
            finally:
                try:
                    os.unlink(temporary, dir_fd=directory_fd)
                except FileNotFoundError:
                    pass
    finally:
        os.close(directory_fd)


def review_native_objective_once(
    material: ObjectiveReviewMaterial,
    numerical_request: NumericalReviewRequest,
    metadata: NativeObjectiveMetadata,
    *,
    registry: Path,
    owner_uid: int,
    run_id: str,
    policy_sha256: str,
    allowed_import_roots: frozenset[str],
    numerical_worker: Callable[[NumericalReviewRequest], NumericalReviewResult],
    gateway: ReviewGateway,
    deadline: float | None = None,
) -> AutomaticReviewBundle:
    """Bind native defaults, then publish/reuse one protected automatic review.

    Only the trusted launcher calls this with captured source and metadata from
    its confined probe. The caller owns review timeout and process cancellation.
    Concurrent jobs reviewing the same identity serialize on one owner-only lock;
    unrelated objectives have distinct locks. No review is performed per epoch.
    Rejected evidence is persisted and reused too; callers must check decision.
    """
    import hashlib

    from agent.schemas.data_analysis.common import canonical_sha256

    from experiments.shared.objective_review_pipeline import review_objective

    material = ObjectiveReviewMaterial.model_validate_json(material.model_dump_json())
    numerical_request = NumericalReviewRequest.model_validate_json(
        numerical_request.model_dump_json()
    )
    metadata = NativeObjectiveMetadata.model_validate_json(metadata.model_dump_json())
    if (
        metadata.source_sha256
        != hashlib.sha256(numerical_request.source.encode()).hexdigest()
        or metadata.package_sha256
        != (
            numerical_request.code_package.sha256
            if numerical_request.code_package
            else None
        )
        or metadata.loss_name != numerical_request.loss_name
        or metadata.effective_parameters != numerical_request.parameters
        or metadata.effective_parameters != material.effective_parameters
        or numerical_request.source not in material.sources.values()
    ):
        raise ValueError("review inputs differ from native objective source/defaults")
    review_id = "r-" + canonical_sha256(
        {
            "run_id": run_id,
            "policy": policy_sha256,
            "material": material.model_dump(mode="json"),
            "numerical": numerical_request.model_dump(mode="json"),
            "metadata": metadata.model_dump(mode="json"),
            "allowed_import_roots": sorted(allowed_import_roots),
        }
    )
    directory_fd = os.open(registry, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    lock_fd = None
    try:
        _require_owned(os.fstat(directory_fd), owner_uid, directory=True)
        if os.geteuid() != owner_uid:
            raise PermissionError("review coordinator must own its registry")
        lock_fd = os.open(
            f"{review_id}.lock",
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600,
            dir_fd=directory_fd,
        )
        _require_owned(os.fstat(lock_fd), owner_uid, directory=False)
        _acquire_review_lock(lock_fd, deadline)
        try:
            payload = _read_record(
                directory_fd, f"{review_id}.evidence.json", owner_uid, limit=4194304
            )
        except FileNotFoundError:
            bundle = review_objective(
                material,
                numerical_request,
                run_id=run_id,
                review_id=review_id,
                policy_sha256=policy_sha256,
                allowed_import_roots=allowed_import_roots,
                numerical_worker=numerical_worker,
                gateway=gateway,
            )
        else:
            bundle = AutomaticReviewBundle.model_validate_json(payload)
            if (
                bundle.receipt.review_id != review_id
                or bundle.receipt.run_id != run_id
                or bundle.receipt.policy_sha256 != policy_sha256
                or bundle.material != material
                or bundle.numerical_request != numerical_request
            ):
                raise ValueError("cached review differs from current native objective")
        # Also verifies the published receipt; repairs evidence-only crash states
        # without repeating an already completed model/API review.
        publish_automatic_review(
            bundle, registry=registry, owner_uid=owner_uid, deadline=deadline
        )
        return bundle
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(directory_fd)
