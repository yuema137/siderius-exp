"""Recover historical cache evidence from hash-pinned original run artifacts.

Run with the selected infra checkout's own Python. This creates a separately
identified replay input; it never edits archives or authorizes in-place resume.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("path")
    @classmethod
    def absolute_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("Recovery artifact paths must be absolute")
        return value

    def read(self) -> bytes:
        data = self.path.read_bytes()
        if hashlib.sha256(data).hexdigest() != self.sha256:
            raise ValueError(f"Artifact digest mismatch: {self.path}")
        return data


class RecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    interpretation: Artifact
    health_policy: Artifact
    run_outputs: tuple[Artifact, ...] = Field(min_length=1)


def recover(request: RecoveryRequest) -> tuple[dict, dict]:
    """Add only evidence/run identity, refusing ambiguous or contradictory inputs."""
    from agent.schemas.hyperparam_tuning import HyperparamTuningOutput
    from agent.schemas.interpretation import InterpretationOutput
    from execute_tools.evaluation_metric import (
        MetricIdentityKey,
        StampedMetricSpec,
        reconcile_metric_identity,
    )
    from execute_tools.health_checks.candidate_eligibility import (
        resolve_scientific_gate_ids,
    )
    from execute_tools.health_checks.config import read_effective_config_body_sha
    from execute_tools.metric_order import MetricOrder
    from nodes.result_interpretation_agent import (
        reconcile_metric_spec,
        tuning_output_to_model_run_summary,
    )

    raw = json.loads(request.interpretation.read())
    interpretation = InterpretationOutput.model_validate(raw)
    request.health_policy.read()
    policy_hash = read_effective_config_body_sha(str(request.health_policy.path))
    if policy_hash is None:
        raise ValueError("The archived effective Health policy has no readable body")
    roster = resolve_scientific_gate_ids(str(request.health_policy.path))
    if roster is None:
        raise ValueError("The archived Health policy does not establish gate roles")

    outputs = [
        HyperparamTuningOutput.model_validate_json(source.read())
        for source in request.run_outputs
    ]
    metric = reconcile_metric_spec(outputs)
    if metric is None:
        raise ValueError("Producing runs have no metric declaration")
    if interpretation.metric_identity is not None:
        identity = interpretation.metric_identity
        reconcile_metric_identity(
            [
                StampedMetricSpec(
                    label="archived interpretation",
                    spec=MetricIdentityKey(identity.metric_id, identity.direction),
                ),
            ],
            bound=metric,
        )
    candidates = []
    for source, output in zip(request.run_outputs, outputs, strict=True):
        if output.health_config_sha256 != policy_hash:
            raise ValueError(
                f"Producing run does not certify this Health policy: {source.path}"
            )
        if output.metric_spec is None:
            raise ValueError(f"Producing run has no metric declaration: {source.path}")
        summary = tuning_output_to_model_run_summary(
            output,
            order=MetricOrder(output.metric_spec),
            required_gate_ids=roster,
        )
        if not hasattr(summary, "formal_evidence"):
            raise ValueError(
                "Select an infra revision supporting independent formal evidence"
            )
        candidates.append((source, summary))

    restored = copy.deepcopy(raw)
    recovered = []
    for model, entry in restored.get("model_knowledge_cache", {}).items():
        stats = entry.get("_stats", {})
        score = stats.get("formal_score")
        if score is None:
            continue
        if isinstance(score, bool) or not isinstance(score, int | float):
            raise TypeError(f"Cached formal score is not numeric: {model}")
        matches = [
            (source, summary)
            for source, summary in candidates
            if summary.model_type == model
            and summary.formal_score == score
            and (stats.get("run_name") is None or stats["run_name"] == summary.run_name)
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one producing formal run for {model}; found {len(matches)}"
            )
        source, summary = matches[0]
        evidence = summary.formal_evidence
        if evidence is None or evidence.model_type != model:
            raise ValueError(
                f"Producing record identity does not match cached model: {model}"
            )
        if summary.scientific_authority != stats.get("scientific_authority"):
            raise ValueError(f"Cached and producing formal authority disagree: {model}")
        encoded = evidence.model_dump(mode="json")
        if stats.get("formal_evidence") not in (None, encoded):
            raise ValueError(
                f"Existing cached formal evidence contradicts the source: {model}"
            )
        stats["formal_evidence"] = encoded
        stats["run_name"] = summary.run_name
        recovered.append(
            {
                "model_type": model,
                "run_name": summary.run_name,
                "exp_id": evidence.exp_id,
                "source": source.model_dump(mode="json"),
            }
        )
    # Detect concurrent source edits across the owner's path-based policy read.
    request.health_policy.read()
    return restored, {
        "schema_version": 1,
        "operation": "recover_formal_evidence",
        "request": request.model_dump(mode="json"),
        "policy_body_sha256": policy_hash,
        "metric_spec": metric.model_dump(mode="json"),
        "required_gate_ids": sorted(roster),
        "recovered": recovered,
        "scope": "Recovered cache inputs; not an in-place resume or full conversation replay",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, required=True, help="New output directory"
    )
    args = parser.parse_args()
    from capture import validate_checkout

    revision = validate_checkout(args.expected_revision)
    request = RecoveryRequest.model_validate_json(args.request.read_bytes())
    restored, receipt = recover(request)
    receipt["infra_revision"] = revision
    receipt["recovery_tool_sha256"] = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()
    args.output.mkdir(parents=True, exist_ok=False)
    payload = (json.dumps(restored, indent=2) + "\n").encode()
    (args.output / "interpretation.json").write_bytes(payload)
    receipt["output_sha256"] = hashlib.sha256(payload).hexdigest()
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        f"Recovered {len(receipt['recovered'])} formal cache entries in {args.output}"
    )


if __name__ == "__main__":
    main()
