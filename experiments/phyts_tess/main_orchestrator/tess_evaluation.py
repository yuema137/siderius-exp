"""The complete evaluator the published metric refuses to run without.

`CandidateEvaluationMetric.require_executor()` raises unless one of these is
bound in the tuner's process. This one exports the trained candidate on the
caller's side, hands it to the coordinator-owned `tess-score` command, and
projects the receipt it gets back. It never scores anything itself.

Shape follows `experiments/tidmad/main_orchestrator/baseline_evaluation.py`
and `native_export.py`. The differences are the task's: one scalar over one
split instead of a banded file vector, and a scorer that runs as the
coordinator account rather than root.

**The evaluator owns inference.** The exporter serializes the model on
synthetic inputs and runs nothing on validation curves. `tess-score` does
that, against the evaluator view's own flux and truth, so a caller cannot
substitute hand-written predictions for a model's output and have them scored.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import torch
from execute_tools.evaluation_execution import (
    CandidateEvaluationRequest,
    CandidateEvaluationResult,
)
from execute_tools.evaluation_metric import (
    MetricResult,
    NotScoreableResult,
    ScoreabilityFailure,
    ScoreabilityVerdict,
    metric_spec_from_declaration,
)
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from experiments.phyts_tess.main_orchestrator.candidate_model import (
    CONTRACT_VERSION,
    MAX_INFERENCE_BATCH,
    TessModelContract,
    candidate_tree_digest,
    load_candidate_model,
    predict_rotation,
    validate_candidate_source,
)
from experiments.phyts_tess.main_orchestrator.tess_receipt import (
    TessEvaluationReceipt,
    read_tess_evaluation,
)
from experiments.shared.native_model_export import export_native_model
from tasks.phyts_tess.runtime.scoreability import TessRotationScoreabilityContract
from tasks.phyts_tess.runtime.tess_data_path import SEQUENCE_LENGTH

__all__ = [
    "TessCandidateEvaluator",
    "TessEvaluationSettings",
    "TessNativeExporter",
    "receipt_result",
]


class TessEvaluationSettings(BaseModel):
    """Operator-selected command and receipt locations. Never credentials."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    #: The installed wrapper, invoked as the coordinator through sudo.
    command: tuple[str, ...] = Field(min_length=1)
    #: Where the caller writes exported candidates; inside the caller's own
    #: workspace and readable by the coordinator.
    candidate_root: Path
    #: Where `tess-score` publishes receipts; coordinator-owned.
    evaluation_root: Path
    run_id: str = Field(min_length=1)
    metric_declaration: Path
    metric_declaration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluator_uid: StrictInt = Field(ge=0)


class TessNativeExporter(BaseModel):
    """Explicit serialization choice; export runs as the research account."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    method: Literal["script", "trace"] = "trace"
    inference_batch_size: int = Field(default=64, ge=1, le=MAX_INFERENCE_BATCH)
    execution_devices: tuple[str, ...] = ("cpu",)

    def __call__(self, request: CandidateEvaluationRequest, destination: Path) -> None:
        contract = TessModelContract(
            version=CONTRACT_VERSION,
            sequence_length=SEQUENCE_LENGTH,
            input_dtype="float32",
            output_kind="continuous_scalar",
            inference_batch_size=self.inference_batch_size,
        )
        # Synthetic inputs: tracing needs representative shapes, not data, and
        # opening validation curves here would give the caller a second path
        # to them. A single curve and a full batch, so both shapes are traced.
        examples = [
            (torch.zeros(1, 1, SEQUENCE_LENGTH, dtype=torch.float32),),
            (
                torch.linspace(
                    -3.0, 3.0, self.inference_batch_size * SEQUENCE_LENGTH
                ).reshape(self.inference_batch_size, 1, SEQUENCE_LENGTH),
            ),
        ]
        export_native_model(
            request,
            destination,
            examples=examples,
            method=self.method,
            execution_devices=self.execution_devices,
        )
        try:
            (destination / "contract.json").write_text(
                contract.model_dump_json(indent=2) + "\n"
            )
            # Reuse the scorer's own loader and forward on the synthetic inputs,
            # so an export the scorer would refuse is refused here first.
            restored, loaded = load_candidate_model(destination, torch.device("cpu"))
            for (example,) in examples:
                predict_rotation(
                    restored,
                    list(example),
                    batch_size=loaded.inference_batch_size,
                    device=torch.device("cpu"),
                )
        except BaseException:
            _set_aside(destination)
            raise


def _set_aside(destination: Path) -> None:
    """Retain a failed export under a name no scorer will accept.

    Nothing is deleted (operator rule). A uniquely named candidate directory
    that failed its own round trip is diagnosis material, and the next attempt
    gets a fresh name anyway.
    """
    aside = destination.with_name(
        f"{destination.name}.failed-export-{int(time.time())}"
    )
    if destination.exists() and not aside.exists():
        destination.rename(aside)


def receipt_result(
    request: CandidateEvaluationRequest,
    receipt: TessEvaluationReceipt,
    path: Path,
) -> CandidateEvaluationResult:
    """Project the scorer's facts; never recompute scientific arithmetic."""
    if receipt.scoreable:
        metric: MetricResult | NotScoreableResult = MetricResult(
            metric_id=request.metric.id,
            direction=request.metric.direction,
            scalar=receipt.scalar,
            per_sample=None,
            references_used=request.metric.references,
        )
    else:
        metric = NotScoreableResult(
            metric_id=request.metric.id,
            direction=request.metric.direction,
            verdict=ScoreabilityVerdict(
                contract_id=request.metric.scoreability.contract_id,
                failures=(
                    ScoreabilityFailure(
                        requirement="finite_complete_split_score",
                        detail="tess-score marked the candidate not scoreable; see receipt.",
                    ),
                ),
            ),
        )
    reasons = [
        str(item["failure_reason"])
        for item in receipt.health_gate_results
        if item.get("failure_reason")
    ]
    reason = (
        None
        if receipt.eligible_for_selection
        else (
            " | ".join(reasons)
            or f"evaluator scoreable={receipt.scoreable}, Health={receipt.health_status}"
        )
    )
    secondary = tuple(
        MetricResult.model_validate(item) for item in receipt.secondary_results
    )
    return CandidateEvaluationResult(
        run_name=request.run_name,
        exp_id=request.exp_id,
        model_type=request.model_type,
        candidate_digest=receipt.candidate_tree_sha256,
        receipt_path=str(path),
        requested_scope=request.requested_scope,
        evaluated_scope={
            "split": receipt.evaluation_split,
            "scope": receipt.evaluation_scope,
            "rows": receipt.evaluated_rows,
        },
        metric=metric,
        health_status=receipt.health_status,
        health_gate_results=receipt.health_gate_results,
        health_config_digest=receipt.health_effective_config_sha256,
        eligible_for_selection=receipt.eligible_for_selection,
        failure_reason=reason,
        secondary_results=secondary,
    )


class TessCandidateEvaluator:
    """Export one trained candidate and invoke the coordinator's scorer.

    The outer supervisor owns the run deadline; no local timeout is added
    here, because killing only this wrapper would leave the scorer's own
    retained work half-written.
    """

    def __init__(
        self,
        settings: TessEvaluationSettings,
        exporter: Callable[[CandidateEvaluationRequest, Path], None],
    ) -> None:
        self.settings = settings
        self.exporter = exporter
        declaration = settings.metric_declaration.read_bytes()
        if (
            hashlib.sha256(declaration).hexdigest()
            != settings.metric_declaration_sha256
        ):
            raise ValueError("frozen metric declaration digest differs from deployment")
        self.metric = metric_spec_from_declaration(
            json.loads(declaration),
            scoreability_contract_types={
                "phyts_tess_rotation_predictions": TessRotationScoreabilityContract
            },
        )

    def evaluate(
        self, request: CandidateEvaluationRequest
    ) -> CandidateEvaluationResult:
        if request.metric.model_dump(mode="json") != self.metric.model_dump(
            mode="json"
        ):
            raise ValueError(
                "requested metric differs from the frozen evaluator declaration"
            )

        settings = self.settings
        invocation = "orchestration-" + uuid.uuid4().hex
        candidate = settings.candidate_root / invocation
        settings.candidate_root.mkdir(parents=True, exist_ok=True)
        self.exporter(request, candidate)
        validate_candidate_source(candidate)
        digest = candidate_tree_digest(candidate)

        completed = subprocess.run(
            [
                *settings.command,
                "--candidate-source",
                str(candidate),
                "--candidate-id",
                invocation,
                "--run-id",
                settings.run_id,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        diagnostic_path = (
            Path(request.workspace) / "evaluation_diagnostics" / f"{invocation}.json"
        )
        diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostic_path.write_text(
            json.dumps(
                {
                    "returncode": completed.returncode,
                    "candidate_path": str(candidate),
                    "candidate_sha256": digest,
                    "stdout": completed.stdout[-32768:],
                    "stderr": completed.stderr[-32768:],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if completed.returncode:
            detail = completed.stderr[-6000:] or completed.stdout[-6000:]
            raise RuntimeError(
                f"tess-score failed (exit {completed.returncode}); trained candidate "
                f"retained at {candidate}; diagnostic: {diagnostic_path}: {detail}"
            )

        lines = completed.stdout.strip().splitlines()
        if len(lines) != 1:
            raise ValueError("tess-score did not return exactly one receipt path")
        output = Path(lines[0])
        expected = settings.evaluation_root / f"{invocation}.json"
        if output != expected:
            raise ValueError("tess-score returned an unrelated receipt path")
        receipt = read_tess_evaluation(
            output,
            candidate_sha256=digest,
            run_id=settings.run_id,
            invocation_id=invocation,
            owner_uid=settings.evaluator_uid,
        )
        return receipt_result(request, receipt, output)
