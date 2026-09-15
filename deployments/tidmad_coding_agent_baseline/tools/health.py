"""Apply the task-declared Health contract to one scored candidate.

The coding-agent baseline deliberately leaves research strategy to the agent.
Eligibility is different: it is evaluator-owned and uses the same generic
HealthGate composition and classifier as an ordinary SIDERIUS workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CandidateHealthEvaluation:
    """Persistable Health evidence and the resulting selection eligibility."""

    status: str
    eligible: bool
    effective_config_sha256: str
    gate_results: list[dict[str, Any]]


def evaluate_candidate_health(
    *,
    input_root: Path,
    raw_data_dir: Path,
    denoised_paths: dict[int, Path],
    file_vector: list[float | None],
    scalar: float,
    candidate_id: str,
    run_id: str,
    config_root: Path,
) -> CandidateHealthEvaluation:
    """Evaluate the explicit task Health binding over exactly this scope.

    ``denoised_paths`` is the trusted scope already resolved by the evaluator,
    not a second agent-selected file list.  Missing, errored, or failed
    blocking evidence therefore fails closed at the selection boundary.
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
    from execute_tools.health_checks.evaluation import (
        evaluate_and_persist_health_gates,
    )

    indices = sorted(denoised_paths)
    if not indices:
        raise ValueError("Health evaluation requires a non-empty candidate scope")
    task_binding = (
        input_root / "tasks" / "tidmad" / "framework_configs" / "health_regression.yaml"
    ).resolve(strict=True)
    dataset_profile = load_dataset_profile(
        str(input_root / "tasks" / "tidmad" / "resolved" / "dataset_profile.json")
    )
    workspace = config_root / ("scope-" + "-".join(str(index) for index in indices))
    workspace.mkdir(parents=True, exist_ok=True)
    effective_path, config_sha = materialize_effective_config(
        source_path=default_health_policy_path(),
        files=indices,
        workspace=str(workspace),
        resolved_scope=indices,
        task_health_binding=str(task_binding),
        dataset_partition_count=20,
    )
    context = HealthCheckContext(
        model_name=candidate_id,
        run_name=run_id,
        round_index=1,
        denoised_paths={index: str(path) for index, path in denoised_paths.items()},
        target_path_fn=lambda index: str(
            raw_data_dir / f"abra_validation_{index:04d}.h5"
        ),
        file_vector=file_vector,
        denoising_score=scalar,
    )
    with bind_dataset_profile(dataset_profile):
        _runtime, persisted, _action = evaluate_and_persist_health_gates(
            context,
            config_path=effective_path,
            production_config_path=default_health_policy_path(),
            task_health_binding=str(task_binding),
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
    return CandidateHealthEvaluation(
        status=status.value,
        eligible=status is CandidateHealthValidity.VALID,
        effective_config_sha256=config_sha,
        gate_results=dumped,
    )
