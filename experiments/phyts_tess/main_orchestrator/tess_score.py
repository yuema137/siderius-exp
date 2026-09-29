"""`tess-score`: the coordinator-side scorer behind the caller's evaluator.

Runs as the coordinator account, invoked by the caller through the installed
sudo wrapper. It snapshots one exported candidate, runs inference over the
COMPLETE validation split against the evaluator view's own flux and truth,
applies the task's scoreability contract, the task's own R-squared metric,
its observational secondaries and its declared Health family, and publishes
one receipt the caller can read but not alter.

Shape follows `deployments/tidmad_coding_agent_baseline/tools/{score,health}.py`.
What differs is the task's geometry (one scalar over one split) and two
deployment facts: the scorer is not root, and nothing is deleted — a scored
candidate is retained, a failed one is set aside under a name that marks it.

Scientific arithmetic lives in the task package, imported FROM THE EVALUATOR
VIEW rather than from the checkout, so the bytes that score are the bytes
the operator froze.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import shutil
import stat
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

__all__ = [
    "RECEIPT_VERSION",
    "TessEvaluatorPolicy",
    "main",
    "read_evaluator_policy",
    "score_candidate",
]

RECEIPT_VERSION = "phyts-tess-orchestration-score-v1"
POLICY_VERSION = "phyts-tess-evaluator-policy-v1"

#: Files the evaluator view must carry, relative to its root.
_VIEW_MANIFEST = Path("tasks/phyts_tess/data/manifests/rotation_identity.csv")
_VIEW_PROFILE = Path("tasks/phyts_tess/declared/dataset_profile.json")
_VIEW_HEALTH = Path("tasks/phyts_tess/declared/task_health.yaml")
_VIEW_METRICS = {
    "r2": Path("tasks/phyts_tess/declared/metric_r2.json"),
    "rmse": Path("tasks/phyts_tess/declared/metric_rmse.json"),
    "mae": Path("tasks/phyts_tess/declared/metric_mae.json"),
}
_SCOREABILITY_TYPES = ("phyts_tess_rotation_predictions",)


class TessEvaluatorPolicy(BaseModel):
    """Evaluator-owned roots and identities; none are selected by the caller."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["phyts-tess-evaluator-policy-v1"]
    caller_uid: StrictInt = Field(ge=0)
    coordinator_uid: StrictInt = Field(ge=0)
    #: The frozen task view carrying `scoring.py` and the identity manifest.
    evaluator_view: Path
    #: Directory holding the staged `tess_rotation_val.npz`.
    validation_data: Path
    #: Every `--candidate-source` must resolve below this caller-owned root.
    candidate_root: Path
    #: Coordinator-private: retained snapshots, deliverables, Health work.
    work_root: Path
    #: Coordinator-owned, caller-readable: one receipt per candidate.
    evaluation_root: Path
    #: The framework's Health policy; `null` selects the packaged default.
    health_policy: Path | None = None
    device: str = "cpu"
    inference_batch_size: int = Field(default=64, ge=1, le=256)

    @model_validator(mode="after")
    def _separate_accounts_and_roots(self) -> TessEvaluatorPolicy:
        if self.caller_uid == self.coordinator_uid:
            raise ValueError("tess-score requires a separate coordinator account")
        roots = [
            self.evaluator_view,
            self.validation_data,
            self.candidate_root,
            self.work_root,
            self.evaluation_root,
        ]
        if any(not root.is_absolute() for root in roots):
            raise ValueError("every evaluator policy path must be absolute")
        if len({str(root) for root in roots}) != len(roots):
            raise ValueError("evaluator policy roots must be distinct")
        return self


def read_evaluator_policy(path: Path, *, owner_uid: int) -> TessEvaluatorPolicy:
    """Read the policy where it lives, with the launcher's file rules.

    Owned by the reading account, not writable by others, exactly one link,
    and every parent root- or owner-owned. A root-owned file is refused for
    the same reason the launcher refuses one: the reader is the coordinator.
    """
    if not path.is_absolute():
        raise ValueError("evaluator policy path must be absolute")
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, owner_uid}:
            raise PermissionError("evaluator policy parents must be operator-owned")
        if info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX:
            raise PermissionError("evaluator policy parent is writable by other users")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != owner_uid
            or info.st_mode & 0o022
            or info.st_nlink != 1
        ):
            raise PermissionError(
                "evaluator policy must be an operator-owned regular file"
            )
        payload = stream.read()
    return TessEvaluatorPolicy.model_validate_json(payload)


# ------------------------------------------------------------------ runtime


def _bind_task_view(view: Path) -> None:
    """Make `tasks.phyts_tess` resolve to the evaluator view, and prove it did.

    The entry script puts the checkout first on `sys.path`; the view goes in
    front of it. If the task package was already imported from anywhere else,
    the frozen bytes are not the ones scoring, and that is refused rather
    than tolerated.
    """
    resolved = view.resolve(strict=True)
    if str(resolved) not in sys.path:
        sys.path.insert(0, str(resolved))
    module = importlib.import_module("tasks.phyts_tess.runtime.tess_data_path")
    origin = Path(str(module.__file__)).resolve()
    if not origin.is_relative_to(resolved):
        raise RuntimeError(
            f"task runtime resolved to {origin}, outside the evaluator view {resolved}"
        )


def _utc_text(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat().replace("+00:00", "Z")


def _contained(root: Path, supplied: Path, *, label: str) -> Path:
    resolved_root = root.resolve(strict=True)
    resolved = supplied.resolve(strict=True)
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"{label} must remain below {resolved_root}: {resolved}")
    return resolved


def _declared_val_rows(view: Path) -> int:
    profile = json.loads((view / _VIEW_PROFILE).read_text(encoding="utf-8"))
    rows = profile["topology"]["populations"]["val"]
    if not isinstance(rows, int) or rows <= 0:
        raise ValueError("dataset profile declares no positive val population")
    return rows


def _model_type(candidate: Path) -> str:
    from experiments.phyts_tess.main_orchestrator.candidate_model import (
        validate_candidate_identity,
    )

    metadata = json.loads((candidate / "native_reconstruction.json").read_text())
    model_type = metadata.get("model_type")
    if not isinstance(model_type, str):
        raise TypeError("native_reconstruction.json names no model_type")
    validate_candidate_identity(model_type)
    return model_type


def _metric(view: Path, name: str, implementation: Any) -> Any:
    from execute_tools.evaluation_metric import metric_spec_from_declaration

    from tasks.phyts_tess.runtime.scoreability import TessRotationScoreabilityContract

    declaration = json.loads((view / _VIEW_METRICS[name]).read_text(encoding="utf-8"))
    spec = metric_spec_from_declaration(
        declaration,
        scoreability_contract_types=dict.fromkeys(
            _SCOREABILITY_TYPES, TessRotationScoreabilityContract
        ),
    )
    if spec.id != name:
        raise ValueError(
            f"{_VIEW_METRICS[name]} declares metric {spec.id!r}, not {name!r}"
        )
    return implementation(spec)


def _evaluate_health(
    *,
    view: Path,
    policy: TessEvaluatorPolicy,
    workspace: Path,
    deliverable: Path,
    payload: object,
    model_type: str,
    run_id: str,
    scalar: float | None,
) -> tuple[str, bool, str, list[dict[str, Any]]]:
    """The task-declared Health family over exactly this deliverable.

    Returns `(status, eligible, effective_config_sha256, persisted_results)`.
    A candidate that was not scoreable has no scalar to classify and is
    `invalid` without running a gate; the effective config is still
    materialized so the receipt names the Health identity it was judged
    under.
    """
    from execute_tools.dataset_config import bind_dataset_profile, load_dataset_profile
    from execute_tools.health_checks import HealthCheckContext
    from execute_tools.health_checks.candidate_eligibility import (
        CandidateHealthValidity,
        classify_candidate_health,
        resolve_scientific_gate_ids,
    )
    from execute_tools.health_checks.config import (
        default_health_policy_path,
        materialize_effective_config,
    )
    from execute_tools.health_checks.evaluation import evaluate_and_persist_health_gates
    from execute_tools.health_checks.schemas import PerSampleEvidence

    source = (
        str(policy.health_policy)
        if policy.health_policy
        else default_health_policy_path()
    )
    binding = str((view / _VIEW_HEALTH).resolve(strict=True))
    workspace.mkdir(parents=True, exist_ok=True)
    effective_path, config_sha = materialize_effective_config(
        source_path=source,
        files=[0],
        workspace=str(workspace),
        resolved_scope=[0],
        task_health_binding=binding,
        dataset_partition_count=1,
    )
    if scalar is None:
        return CandidateHealthValidity.INVALID.value, False, config_sha, []

    context = HealthCheckContext(
        model_name=model_type,
        run_name=run_id,
        round_index=1,
        denoised_paths={0: str(deliverable)},
        evaluation_payload_fn=lambda: payload,
        file_vector=[],
        denoising_score=scalar,
        # The R-squared metric is scalar-only (`per_sample=None`), and the
        # task's Health family reads the deliverable through its own view
        # provider rather than a per-file vector — D18, stated not inferred.
        per_sample_evidence=PerSampleEvidence.SCALAR_ONLY,
    )
    profile = load_dataset_profile(str(view / _VIEW_PROFILE))
    with bind_dataset_profile(profile):
        _runtime, persisted, _action = evaluate_and_persist_health_gates(
            context,
            config_path=effective_path,
            production_config_path=source,
            task_health_binding=binding,
            healthgate_mode="enforce",
            result_authority="task_health",
        )
    dumped = [item.model_dump(mode="json") for item in persisted]
    required = resolve_scientific_gate_ids(effective_path)
    status = classify_candidate_health(
        {
            "status": "success",
            "denoising_score": scalar,
            "health_gate_enabled": True,
            "health_gate_results": dumped,
        },
        required_gate_ids=required,
    )
    return status.value, status is CandidateHealthValidity.VALID, config_sha, dumped


def _write_json(path: Path, payload: Any, *, mode: int) -> None:
    """Create-once: the path must not exist, and the bytes are durable on return."""
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _set_aside(staging: Path, retained: Path) -> None:
    """A failed evaluation is renamed, never removed."""
    aside = retained.with_name(f"{retained.name}.failed-{int(time.time())}")
    if staging.exists() and not aside.exists():
        staging.rename(aside)


def score_candidate(
    policy: TessEvaluatorPolicy,
    *,
    candidate_source: Path,
    candidate_id: str,
    run_id: str,
) -> Path:
    """Score one candidate over the complete validation split; return the receipt path."""
    _bind_task_view(policy.evaluator_view)
    import torch
    from execute_tools.evaluation_metric import MetricResult
    from execute_tools.task_data_path import (
        DeliverableWriteRequest,
        EvalMaterializationParams,
        EvaluationReadRequest,
        ScopeBuildRequest,
    )

    from experiments.phyts_tess.main_orchestrator.candidate_model import (
        candidate_tree_digest,
        load_candidate_model,
        predict_rotation,
        validate_candidate_identity,
        validate_candidate_source,
    )
    from experiments.phyts_tess.main_orchestrator.tess_receipt import (
        TessEvaluationReceipt,
    )
    from tasks.phyts_tess.runtime.scoring import (
        TessRotationMaeMetric,
        TessRotationR2Metric,
        TessRotationRmseMetric,
    )
    from tasks.phyts_tess.runtime.tess_data_path import (
        PhytsTessTaskDataPath,
        deliverable_name,
    )

    validate_candidate_identity(candidate_id)
    if not run_id:
        raise ValueError("run id must be non-empty")
    view = policy.evaluator_view.resolve(strict=True)
    source = _contained(
        policy.candidate_root, candidate_source, label="candidate source"
    )
    receipt_path = policy.evaluation_root / f"{candidate_id}.json"
    retained = policy.work_root / "candidates" / candidate_id
    staging = retained.with_name(f".{candidate_id}.staging")
    if receipt_path.exists() or retained.exists() or staging.exists():
        raise FileExistsError(f"candidate {candidate_id} was already evaluated")
    retained.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    policy.evaluation_root.mkdir(parents=True, exist_ok=True)

    staging.mkdir(mode=0o750)
    try:
        snapshot = staging / "candidate"
        # Links are copied as links so an evaluator-owned copy cannot
        # dereference a caller-created link into hidden truth.
        shutil.copytree(source, snapshot, symlinks=True)
        validate_candidate_source(snapshot)
        digest = candidate_tree_digest(snapshot)
        model_type = _model_type(snapshot)

        task = PhytsTessTaskDataPath(manifest_path=str(view / _VIEW_MANIFEST))
        scope = task.build_eval_scope(
            ScopeBuildRequest(
                round_kind="formal", selection_strategy="snapshot", portion=1.0
            )
        )
        declared_rows = _declared_val_rows(view)
        rows = len(scope.rows)
        if rows != declared_rows:
            raise ValueError(
                f"evaluator view builds a {rows}-row val scope; the profile declares "
                f"{declared_rows}"
            )
        dataset = task.validation_dataset(
            scope, EvalMaterializationParams(data_dir=str(policy.validation_data))
        )
        inputs = [dataset[index][0] for index in range(rows)]

        device = torch.device(policy.device)
        model, contract = load_candidate_model(snapshot, device)
        predictions = predict_rotation(
            model,
            inputs,
            batch_size=min(contract.inference_batch_size, policy.inference_batch_size),
            device=device,
        )

        deliverable_dir = staging / "deliverable"
        write_request = DeliverableWriteRequest(
            output_dir=str(deliverable_dir),
            exp_id=candidate_id,
            run_name=run_id,
            model_type=model_type,
            task_scope=scope,
        )
        task.write_deliverable(predictions, write_request)
        read_request = EvaluationReadRequest(
            deliverable_dir=str(deliverable_dir),
            exp_id=candidate_id,
            run_name=run_id,
            model_type=model_type,
        )
        deliverable = deliverable_dir / deliverable_name(read_request)
        payload = task.read_evaluation_payload(read_request)
        compute_kwargs = {
            "evaluation_payload": payload,
            "task_scope": scope,
            "data_dir": str(policy.validation_data),
        }
        deliverables = {0: str(deliverable)}

        outcome = _metric(view, "r2", TessRotationR2Metric).evaluate(
            deliverables, **compute_kwargs
        )
        scalar: float | None = None
        refusal: dict[str, Any] | None = None
        if isinstance(outcome, MetricResult) and outcome.scalar is not None:
            scalar = float(outcome.scalar)
            if not math.isfinite(scalar):
                scalar = None
        else:
            refusal = outcome.model_dump(mode="json")
        scoreable = scalar is not None

        secondary_results: list[dict[str, Any]] = []
        secondary_refusals: list[dict[str, Any]] = []
        if scoreable:
            for name, implementation in (
                ("rmse", TessRotationRmseMetric),
                ("mae", TessRotationMaeMetric),
            ):
                result = _metric(view, name, implementation).evaluate(
                    deliverables, **compute_kwargs
                )
                target = (
                    secondary_results
                    if isinstance(result, MetricResult)
                    else secondary_refusals
                )
                target.append(result.model_dump(mode="json"))

        status, health_passed, config_sha, gate_results = _evaluate_health(
            view=view,
            policy=policy,
            workspace=staging / "health",
            deliverable=deliverable,
            payload=payload,
            model_type=model_type,
            run_id=run_id,
            scalar=scalar,
        )
        scored_epoch = time.time()
        receipt: dict[str, Any] = {
            "version": RECEIPT_VERSION,
            "scalar": scalar,
            "scoreable": scoreable,
            "valid": bool(scoreable and health_passed),
            "evaluation_split": "val",
            "evaluation_scope": "complete-split",
            "evaluated_rows": len(predictions),
            "declared_rows": declared_rows,
            "candidate_tree_sha256": digest,
            "run_id": run_id,
            "invocation_id": candidate_id,
            "health_status": status,
            "health_passed": health_passed,
            "health_gate_results": gate_results,
            "health_effective_config_sha256": config_sha,
            "eligible_for_selection": bool(scoreable and health_passed),
            "secondary_results": secondary_results,
            "secondary_refusals": secondary_refusals,
            "metric_refusal": refusal,
            "model_type": model_type,
            "score_epoch": int(scored_epoch),
            "score_utc": _utc_text(scored_epoch),
        }
        # The reader's constraints hold at the writer: a receipt that would
        # be refused on the caller's side is refused here, with the candidate
        # set aside for diagnosis rather than a receipt nobody can read.
        TessEvaluationReceipt.model_validate(receipt)
        _write_json(staging / "score.json", receipt, mode=0o440)
        staging.rename(retained)
    except BaseException:
        _set_aside(staging, retained)
        raise

    _write_json(receipt_path, receipt, mode=0o444)
    return receipt_path


# ---------------------------------------------------------------------- cli


def _authorize(policy: TessEvaluatorPolicy) -> None:
    """The same shape as the launcher's rule: coordinator running, caller calling."""
    if os.geteuid() != policy.coordinator_uid or os.geteuid() == policy.caller_uid:
        raise PermissionError("tess-score requires its separate coordinator account")
    sudo_uid = os.environ.get("SUDO_UID")
    if sudo_uid is None or not sudo_uid.isdigit() or int(sudo_uid) != policy.caller_uid:
        raise PermissionError(
            "tess-score must be invoked by the caller account through sudo"
        )


def main(policy_path: Path, argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="tess-score")
    parser.add_argument("--candidate-source", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(list(argv))
    policy = read_evaluator_policy(policy_path, owner_uid=os.geteuid())
    _authorize(policy)
    receipt = score_candidate(
        policy,
        candidate_source=args.candidate_source,
        candidate_id=args.candidate_id,
        run_id=args.run_id,
    )
    print(receipt)
    return 0
