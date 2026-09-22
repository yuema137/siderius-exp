"""Bounded native train/export/infer/score qualification, without LLM calls.

Run with this checkout's interpreter and -m. This uses an operator-owned
tiny model and is not evidence of autonomous proposal generation or isolation.
The original task declarations and prepared arrays are never modified.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import yaml
from core.sandbox_executor import TidmadSandbox
from core.training_execution_bindings import TrainingExecutionBindings
from execute_tools.task_data_path import EvaluationReadRequest, ScopeBuildRequest
from ml_models.models_format_sandbox import TrainConfig
from workflows.task_composition import (
    bind_run_task_composition,
    compose_run_task_bindings,
)


def qualify(
    composition_path: Path, data: Path, workspace: Path, device: str, attempts: int,
    training_config: TrainConfig | None = None,
) -> dict:
    workspace.mkdir(parents=True, exist_ok=False)
    source = yaml.safe_load(composition_path.read_text())

    def absolute_refs(value, key=""):
        if isinstance(value, dict):
            return {k: absolute_refs(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [absolute_refs(v) for v in value]
        if isinstance(value, str) and key in {
            "file",
            "ref",
            "declaration",
            "config",
            "dir",
        }:
            return str((composition_path.parent / value).resolve())
        return value

    qualified = absolute_refs(source)
    plugins = workspace / "smoke_plugins"
    plugins.mkdir()
    fixture = (
        Path(__file__).resolve().parents[2] / "tests/fixtures/prepared_smoke_model.py"
    )
    shutil.copyfile(fixture, plugins / fixture.name)
    qualified["model_plugins"] = {
        "dir": str(plugins),
        "require": ["prepared_smoke_regressor"],
    }
    manifest = workspace / "smoke_composition.yaml"
    manifest.write_text(yaml.safe_dump(qualified, sort_keys=False))
    composition = compose_run_task_bindings(str(manifest))
    adapter = composition.task_data_path
    req = ScopeBuildRequest(
        round_kind="formal", selection_strategy="snapshot", portion=1.0, seed=17
    )
    scopes = SimpleNamespace(
        training=adapter.build_training_scope(
            req.model_copy(update={"max_samples": 128})
        ),
        evaluation=adapter.build_eval_scope(req),
        training_validation=adapter.build_eval_scope(
            req.model_copy(update={"portion": 0.1})
        ),
    )
    assert tuple(scopes.training_validation.rows) == tuple(
        np.load(data / "evaluator/validation/loss_indices.npy", allow_pickle=False)
    )
    record = {
        "task_id": adapter.task_data_path_id,
        "device": device,
        "train_rows": scopes.training.row_count,
        "loss_rows": scopes.training_validation.row_count,
        "formal_rows": scopes.evaluation.row_count,
        "claim_boundary": "Native subprocess qualification only; no autonomous LLM or private-worker isolation claim.",
        "attempts": [],
    }
    model_type = "prepared_smoke_regressor"
    model = {
        "model_type": model_type,
        "segmentation_size": adapter.declaration.length,
        "batch_size": 16,
    }
    training = {
        "epochs": 1,
        "batch_size": 16,
        "lr": 1e-3,
        "optimizer_type": "adam",
        "device": device,
    }
    if training_config is not None:
        training = training_config.model_dump(mode="json")
        training["device"] = device
        model["batch_size"] = training_config.batch_size
    record["training_config"] = training
    loss = {"loss_type": "smooth_l1", "reduction": "mean"}
    with bind_run_task_composition(composition, physical_data_root=str(data)):
        sandbox = TidmadSandbox(
            workspace=str(workspace),
            run_name="qualification",
            progress_bar=False,
            file_index=0,
        )
        for number in range(attempts):
            exp_id = f"attempt_{number}"
            entry = {"exp_id": exp_id, "phases": {}}
            record["attempts"].append(entry)
            calls = {
                "training": lambda exp_id=exp_id, number=number: (
                    sandbox.execute_training(
                        exp_id,
                        "qualification",
                        model_type,
                        model,
                        training,
                        loss,
                        train_base_seed=17 + number,
                        execution_bindings=TrainingExecutionBindings(
                            task_scopes=scopes
                        ),
                    )
                ),
                "inference": lambda exp_id=exp_id: sandbox.execute_inference(
                    exp_id,
                    "qualification",
                    model_type,
                    model,
                    loss,
                    inference_batch=64,
                    task_scopes=scopes,
                ),
                "scoring": lambda exp_id=exp_id: sandbox.execute_scoring(
                    exp_id,
                    "qualification",
                    model_type,
                    model,
                    training,
                    loss,
                    task_scopes=scopes,
                ),
            }
            for phase, call in calls.items():
                started = time.monotonic()
                result = call()
                entry["phases"][phase] = {
                    "wall_seconds": time.monotonic() - started,
                    "result": result,
                }
                (workspace / "receipt.json").write_text(
                    json.dumps(record, indent=2, default=str)
                )
                print(
                    json.dumps(
                        {
                            "attempt": number,
                            "phase": phase,
                            "seconds": entry["phases"][phase]["wall_seconds"],
                            "status": result.get("status"),
                        }
                    ),
                    flush=True,
                )
                if result.get("status") != "success":
                    raise RuntimeError(
                        f"{phase} failed; see {workspace / 'receipt.json'}"
                    )
            payload = adapter.read_evaluation_payload(
                EvaluationReadRequest(
                    deliverable_dir=str(workspace),
                    run_name="qualification",
                    exp_id=exp_id,
                    model_type=model_type,
                )
            )
            assert len(payload) == scopes.evaluation.row_count
            predictions = np.asarray(
                [payload[k] for k in scopes.evaluation.keys], dtype=np.float64
            )
            truth = scopes.evaluation.truth(str(data))
            independent = float(np.sqrt(np.mean(np.square(predictions - truth))))
            training_result = entry["phases"]["training"]["result"]["results"]
            history = training_result["training_history"]
            assert (
                history["validation_requested_samples"]
                == scopes.training_validation.row_count
            )
            assert history["validation_samples"] == scopes.training_validation.row_count
            # Same exported model, same fixed subset, same loss: detect an
            # export/restore or target-unit change across native subprocesses.
            indices = list(scopes.training_validation.rows)
            error = np.abs(predictions[indices] - truth[indices])
            transform = training_result.get("target_standardization")
            if training.get("target_standardization") == "training_pool_global":
                assert transform is not None
                targets = np.load(data / "training/targets.npy", mmap_mode="r")
                selected = np.asarray(targets[list(scopes.training.rows)], dtype=np.float64)
                assert transform["training_rows"] == scopes.training.row_count
                assert np.isclose(transform["mean"], selected.mean(), rtol=1e-10)
                assert np.isclose(transform["scale"], selected.std(), rtol=1e-10)
                error = error / transform["scale"]
            if training.get("drop_last") is False:
                assert history["training_samples"] == [scopes.training.row_count] * len(
                    history["validation_objective"]
                )
            selected_loss = history["validation_objective"][-1]
            if training.get("checkpoint_selection") == "best_validation_loss":
                selection = training_result["selected_checkpoint"]
                selected_loss = min(history["validation_objective"])
                assert selection["validation_loss"] == selected_loss
            restored_loss = float(
                np.where(error < 1, 0.5 * error**2, error - 0.5).mean()
            )
            assert np.isclose(
                restored_loss, selected_loss, rtol=1e-5, atol=1e-6
            )
            entry["restored_validation_loss"] = restored_loss
            metric = entry["phases"]["scoring"]["result"]["results"]["metric_result"]
            independent_r2 = float(
                1
                - np.sum((predictions - truth) ** 2)
                / np.sum((truth - truth.mean()) ** 2)
            )
            assert metric["metric_id"] == "r2" and metric["direction"] == "higher"
            assert np.isclose(metric["scalar"], independent_r2, rtol=1e-10)
            entry["independent_r2"] = independent_r2
            entry["independent_rmse"] = independent
            (workspace / "receipt.json").write_text(
                json.dumps(record, indent=2, default=str)
            )
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--composition", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--attempts", type=int, choices=(1, 2), default=2)
    parser.add_argument("--training-config", type=Path,
                        help="Optional native TrainConfig JSON for bounded policy qualification")
    args = parser.parse_args()
    qualify(
        args.composition.resolve(),
        args.data_dir.resolve(),
        args.workspace.resolve(),
        args.device,
        args.attempts,
        TrainConfig.model_validate_json(args.training_config.read_text())
        if args.training_config else None,
    )


if __name__ == "__main__":
    main()
