"""Drive one bounded tuner run through the deployment's bindings, as the caller.

`SUBMISSION.md`'s binding, executable, for `SMOKE.md` steps 2–4: bind the
public composition, the complete evaluator and the protected validation
launcher in one process, run the native tuner for a short explicit epoch
budget, and report every receipt it earned. It chooses no research
strategy — the planner and reflector are the run's declared models — and
it is not the outer controller; it is what that controller's first call
looks like when nothing else is in the way.

Run it by PATH from the published runtime with the framework interpreter,
from the caller account, inside the supervisor's clock:

    <framework-python> <runtime>/experiments/phyts_tess/main_orchestrator/smoke_tuner.py \\
        --workspace /home/tess-caller/workspace/<run-id> --run-id <run-id> \\
        --storage-root /home/tess-caller/work --composition <caller>/composition.yaml \\
        --data-dir <rundata> --unit-dir .   # the supervisor's cwd holds launch.json

Every bound the run declaration fixes is fixed here too; only the epoch
budget is short, because a smoke measures the path and not the model.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

__all__ = ["build_smoke_input", "main"]

#: The run declaration's execution bounds (`bundle/execution-policy.json`,
#: projected from `main_fixed_workflow/workflow.json`). Not API defaults.
EXECUTION_BOUNDS: dict[str, Any] = {
    "trial_time_budget_minutes": 5,
    "formal_time_budget_minutes": 15,
    "trial_vram_budget_gb": 8,
    "formal_vram_budget_gb": 8,
    "formal_training_scope_source": "operator",
    "formal_portion": 1.0,
    "formal_train_portion": 1.0,
    "formal_eval_portion": 1.0,
    "training_budget_reserve_fraction": 0.2,
    "runtime_watchdog_enabled": False,
}

#: The environment variable each provider's bridge reads (installation guide,
#: "API keys"). Only the declared provider's key is required.
PROVIDER_CREDENTIALS = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}

#: All roles route here per `SIDERIUS-RUN.md`.
MODEL_ROUTING = {
    "provider": "openai",
    "model_id": "gpt-5.6-sol",
    "reasoning_effort": "medium",
}


def build_smoke_input(
    *,
    run_id: str,
    storage_workspace: Path,
    data_dir: Path,
    task_description: str,
    task_composition_ref: Any,
    model_type: str,
    max_epochs: int,
    rounds: int,
) -> Any:
    """The tuner input: declared bounds, declared routing, a short epoch budget.

    Two rounds with `is_trial` pinned on round 1 is the fixed workflow's
    shape (one trial, then one formal), so the smoke exercises both the
    trial and the complete-split formal evaluation.
    """
    from agent.schemas.hyperparam_tuning import HyperparamTuningInput

    if max_epochs < 1 or rounds < 1:
        raise ValueError("the smoke needs at least one epoch and one round")
    payload: dict[str, Any] = {
        "model_type": model_type,
        "task_description": task_description,
        "max_rounds": rounds,
        "is_trial": True,
        "plan_overrides": {"is_trial": True},
        "max_epochs": max_epochs,
        "trial_max_epochs": max_epochs,
        "formal_max_epochs": max_epochs,
        "healthgate_mode": "blocking",
        "result_authority": "scientific",
        "health_gate_enabled": True,
        "llm_provider": MODEL_ROUTING["provider"],
        "llm_model_id": MODEL_ROUTING["model_id"],
        "reasoning_effort": MODEL_ROUTING["reasoning_effort"],
        "reflect_provider": MODEL_ROUTING["provider"],
        "reflect_model_id": MODEL_ROUTING["model_id"],
        "reflect_reasoning_effort": MODEL_ROUTING["reasoning_effort"],
        "storage": {
            "backend": "local",
            "local": {"workspace": str(storage_workspace), "run_name": run_id},
        },
        "data_dir": str(data_dir),
        "task_composition_ref": task_composition_ref,
        **EXECUTION_BOUNDS,
    }
    return HyperparamTuningInput.model_validate(payload)


def _receipts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What the evaluator returned, per record, without recomputing anything."""
    summary = []
    for record in records:
        evaluation = record.get("external_evaluation")
        if not isinstance(evaluation, dict):
            continue
        metric = evaluation.get("metric") or {}
        summary.append(
            {
                "exp_id": record.get("exp_id"),
                "receipt_path": evaluation.get("receipt_path"),
                "eligible_for_selection": evaluation.get("eligible_for_selection"),
                "scalar": metric.get("scalar"),
                "health_status": evaluation.get("health_status"),
                "failure_reason": evaluation.get("failure_reason"),
            }
        )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace", type=Path, required=True, help="the assembled agent workspace"
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--storage-root", type=Path, required=True, help="the caller's work root"
    )
    parser.add_argument("--composition", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    clock = parser.add_mutually_exclusive_group(required=True)
    clock.add_argument("--deadline-epoch", type=float, help="the unit's deadline")
    clock.add_argument(
        "--unit-dir",
        type=Path,
        help="read the deadline from this unit's launch.json (the supervisor's cwd)",
    )
    parser.add_argument("--model-type", default="tess_reference_cnn")
    parser.add_argument("--max-epochs", type=int, default=2)
    parser.add_argument("--rounds", type=int, default=2)
    args = parser.parse_args(argv)

    # The published runtime is a source distribution: this file's root is the
    # import root for `experiments.*`, exactly as `SIDERIUS-RUN.md` states.
    runtime_root = Path(__file__).resolve().parents[3]
    if str(runtime_root) not in sys.path:
        sys.path.insert(0, str(runtime_root))
    deadline = args.deadline_epoch
    if deadline is None:
        # The supervisor writes the record before it spawns the caller, and
        # spawns it with the unit directory as cwd, so `--unit-dir .` works.
        record = json.loads((args.unit_dir / "launch.json").read_text(encoding="utf-8"))
        deadline = float(record["deadline_epoch"])
    if time.time() >= deadline:
        raise SystemExit("the unit deadline has already passed; nothing launched")
    # Name-only presence check for the declared provider's credential. Without
    # it every attempt fails with a 401 and the run burns its whole attempt
    # budget in a minute — observed on the first smoke launch.
    credential = PROVIDER_CREDENTIALS[MODEL_ROUTING["provider"]]
    if not os.environ.get(credential):
        raise SystemExit(
            f"{credential} is not set in this process; the run routes every role "
            f"to {MODEL_ROUTING['provider']} and cannot start without it"
        )

    from core.generated_library import bind_generated_library_to_workspace
    from execute_tools.evaluation_execution import bind_candidate_evaluation
    from execute_tools.validation_execution import (
        ValidationDeployment,
        bind_validation_deployment,
    )
    from nodes.ml_hyperparameter_tune_agent.ml_hyperparameter_tune_agent import (
        HyperparamTuningAgent,
    )
    from workflows.task_composition import (
        bind_run_task_composition,
        build_task_composition_ref,
        compose_run_task_bindings,
    )

    from experiments.phyts_tess.main_orchestrator.tess_evaluation import (
        TessCandidateEvaluator,
        TessEvaluationSettings,
        TessNativeExporter,
    )

    run_dir = args.workspace / "run"
    evaluation = TessEvaluationSettings.model_validate_json(
        (run_dir / "evaluation-settings.json").read_bytes()
    )
    if evaluation.run_id != args.run_id:
        raise SystemExit(
            f"evaluation settings are for run {evaluation.run_id!r}, not {args.run_id!r}"
        )
    declared = ValidationDeployment.model_validate_json(
        (run_dir / "validation-settings.json").read_bytes()
    )
    validation = declared.model_copy(
        update={"settings": {**declared.settings, "deadline_epoch": deadline}}
    )
    storage_workspace = args.storage_root / args.run_id
    storage_workspace.mkdir(parents=True, exist_ok=True)
    evaluation.candidate_root.mkdir(parents=True, exist_ok=True)

    bind_generated_library_to_workspace(str(storage_workspace))
    composition = compose_run_task_bindings(str(args.composition))
    evaluator = TessCandidateEvaluator(
        evaluation, TessNativeExporter(method="trace", inference_batch_size=64)
    )
    agent_input = build_smoke_input(
        run_id=args.run_id,
        storage_workspace=storage_workspace,
        data_dir=args.data_dir,
        task_description=composition.task_description,
        task_composition_ref=build_task_composition_ref(composition),
        model_type=args.model_type,
        max_epochs=args.max_epochs,
        rounds=args.rounds,
    )
    started = time.time()
    with (
        bind_run_task_composition(composition, physical_data_root=str(args.data_dir)),
        bind_candidate_evaluation(evaluator),
        bind_validation_deployment(validation),
    ):
        output = HyperparamTuningAgent().run(agent_input)

    summary = {
        "run_id": args.run_id,
        "status": output.status,
        "completed_rounds": output.completed_rounds,
        "elapsed_seconds": round(time.time() - started, 1),
        "receipts": _receipts(list(output.all_records)),
    }
    (run_dir / "smoke-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if output.status == "completed" and summary["receipts"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
