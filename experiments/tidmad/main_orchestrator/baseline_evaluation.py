"""Research-side client of the unchanged complete-band baseline evaluator."""

import hashlib
import json
import os
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from agent.schemas.data_analysis.common import Sha256
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
from pydantic import BaseModel, ConfigDict, Field

from deployments.tidmad_coding_agent_baseline.tools.archive_candidate import (
    candidate_tree_digest,
    validate_candidate_source,
)
from experiments.tidmad.main_orchestrator.baseline_receipt import (
    BaselineEvaluationReceipt,
    read_baseline_evaluation,
)
from tasks.tidmad.runtime.scoreability import TidmadScoreabilityContract


class BaselineEvaluationSettings(BaseModel):
    """Operator-selected public command and original evaluator output locations."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    band: Literal["0-3", "4-9", "10-14", "15-19"]
    command: tuple[str, ...] = Field(min_length=1)
    archive_root: Path
    evaluation_root: Path
    candidate_root: Path
    run_id: str = Field(min_length=1)
    metric_declaration: Path
    metric_declaration_sha256: Sha256
    evaluator_uid: int = Field(default=0, ge=0)


class BaselineCommandDiagnostic(BaseModel):
    """Bounded public-command output; no environment or private files are read."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    returncode: int
    candidate_path: str
    candidate_sha256: Sha256
    stdout: str = Field(max_length=32768)
    stderr: str = Field(max_length=32768)


def receipt_result(
    request: CandidateEvaluationRequest,
    receipt: BaselineEvaluationReceipt,
    path: Path,
) -> CandidateEvaluationResult:
    """Project original evaluator facts; never recompute scientific arithmetic."""
    payload = receipt.model_dump(mode="json")
    if receipt.scoreable:
        metric = MetricResult(
            metric_id=request.metric.id,
            direction=request.metric.direction,
            scalar=receipt.scalar,
            per_sample=list(receipt.file_vector),
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
                        requirement="finite_complete_band_score",
                        detail="Original evaluator marked the candidate not scoreable; see receipt.",
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
            "sample_set": payload.get("sample_set"),
        },
        metric=metric,
        health_status=receipt.health_status,
        health_gate_results=receipt.health_gate_results,
        health_config_digest=receipt.health_effective_config_sha256,
        eligible_for_selection=receipt.eligible_for_selection,
        failure_reason=reason,
    )


class BaselineCandidateEvaluator:
    """Export one trained candidate and invoke the installed baseline command.

    The exporter runs in the research account and creates a fresh directory.
    The existing outer supervisor owns the run deadline and privileged scorer
    cleanup. No independent local timeout is added: killing only the public
    wrapper would leave the original evaluator's transient inference services.
    """

    def __init__(
        self,
        settings: BaselineEvaluationSettings,
        exporter: Callable[[CandidateEvaluationRequest, Path], None],
    ):
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
                "tidmad_denoised_h5": TidmadScoreabilityContract
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
        if request.secondary_metrics:
            raise ValueError("baseline evaluator does not expose secondary metrics")
        settings = self.settings
        invocation = "orchestration-" + uuid.uuid4().hex
        candidate = settings.candidate_root / invocation
        settings.candidate_root.mkdir(parents=True, exist_ok=True)
        self.exporter(request, candidate)
        validate_candidate_source(candidate)
        digest = candidate_tree_digest(candidate)
        environment = dict(os.environ)
        environment.update(
            BASELINE_RUN_ID=settings.run_id, BASELINE_INVOCATION_ID=invocation
        )
        completed = subprocess.run(
            [
                *settings.command,
                "--band",
                settings.band,
                "--candidate-id",
                invocation,
                "--candidate-source",
                str(candidate),
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        diagnostic = BaselineCommandDiagnostic(
            returncode=completed.returncode,
            candidate_path=str(candidate),
            candidate_sha256=digest,
            stdout=completed.stdout[-32768:],
            stderr=completed.stderr[-32768:],
        )
        diagnostic_path = (
            Path(request.workspace) / "evaluation_diagnostics" / f"{invocation}.json"
        )
        diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
        diagnostic_path.write_text(diagnostic.model_dump_json(indent=2) + "\n")
        if completed.returncode:
            detail = diagnostic.stderr[-6000:] or diagnostic.stdout[-6000:]
            raise RuntimeError(
                f"baseline evaluator failed (exit {completed.returncode}); "
                f"trained candidate retained at {candidate}; "
                f"diagnostic: {diagnostic_path}; "
                f"evaluation may be retried with the existing candidate: {detail}"
            )
        lines = completed.stdout.strip().splitlines()
        if len(lines) != 1:
            raise ValueError(
                "baseline evaluator did not return exactly one receipt path"
            )
        output = Path(lines[0])
        archive = settings.archive_root / settings.band / invocation
        feedback = settings.evaluation_root / settings.band / f"{invocation}.json"
        if output == archive:
            score = archive / "score.json"
        elif output == feedback:
            score = feedback
        else:
            raise ValueError("baseline evaluator returned an unrelated receipt path")
        receipt = read_baseline_evaluation(
            score,
            band=settings.band,
            candidate_sha256=digest,
            run_id=settings.run_id,
            invocation_id=invocation,
            owner_uid=settings.evaluator_uid,
        )
        return receipt_result(request, receipt, score)
