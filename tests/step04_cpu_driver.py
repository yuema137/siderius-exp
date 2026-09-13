from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def run_phases(task: str, exp: Path, workspace: Path, data: Path):
    from core.sandbox_executor import TidmadSandbox
    from execute_tools.health_checks._composition import HealthBindingState
    from execute_tools.task_data_path import (
        EvaluationReadRequest,
        ScopeBuildRequest,
        resolve_task_scope_capability,
    )
    from workflows.task_composition import (
        bind_run_task_composition,
        compose_run_task_bindings,
    )

    manifest = (
        exp
        / "tasks"
        / task
        / "compositions"
        / ("signal_background.yaml" if "supernemo" in task else "low_avse.yaml")
    )
    composition = compose_run_task_bindings(str(manifest))
    cap = resolve_task_scope_capability(composition.task_data_path)
    req = ScopeBuildRequest(
        round_kind="formal",
        selection_strategy="snapshot",
        portion=1.0,
        max_samples=4,
        seed=17,
    )
    scopes = SimpleNamespace(
        training=cap.build_training_scope(req), evaluation=cap.build_eval_scope(req)
    )
    mod = sys.modules[type(composition.task_data_path).__module__]
    tr, ev = (
        mod.materialize_scope(scopes.training, data),
        mod.materialize_scope(scopes.evaluation, data),
    )
    assert len(tr.labels) == len(ev.labels) == 4
    assert (scopes.training.role, scopes.evaluation.role) == (
        ("train", "validation") if "supernemo" in task else ("train", "test")
    )
    assert set(map(int, tr.event_ids)).isdisjoint(set(map(int, ev.event_ids)))
    model = (
        "supernemo_reference_pointnet"
        if "supernemo" in task
        else "majorana_reference_cnn"
    )
    mc = (
        {"model_type": model, "segmentation_size": 224, "hidden_dim": 32}
        if "supernemo" in task
        else {"model_type": model, "segmentation_size": 3800, "width": 16}
    )
    tc = {
        "lr": 1e-3,
        "epochs": 1,
        "batch_size": 2,
        "optimizer_type": "adam",
        "device": "cpu",
    }
    lc = {"loss_type": "ce", "reduction": "mean"}
    commands = []

    def audit(event, values):
        if event == "subprocess.Popen":
            exe, argv, cwd, _env = values
            if list(argv[1:4]) == ["-m", "core.local_code.child", "script"]:
                assert "PYTHONPATH" not in _env
                assert _env.get("SIDERIUS_TASK_CODE_MANIFEST")
                assert _env.get("SIDERIUS_TASK_CODE_SHA256")
                safe = {
                    k: _env.get(k)
                    for k in (
                        "CUDA_VISIBLE_DEVICES",
                        "OMP_NUM_THREADS",
                        "MKL_NUM_THREADS",
                        "OPENBLAS_NUM_THREADS",
                        "SIDERIUS_GENERATED_LIBRARY_DIR",
                        "SIDERIUS_CHAIN_WORKSPACE",
                        "SIDERIUS_PLUGIN_DIRS",
                        "SIDERIUS_LOSS_DIRS",
                        "SIDERIUS_TASK_CODE_MANIFEST",
                        "SIDERIUS_TASK_CODE_SHA256",
                    )
                }
                commands.append(
                    {
                        "executable": exe,
                        "argv": argv,
                        "target_argv": [exe, *argv[4:]],
                        "cwd": cwd,
                        "env_safe": safe,
                    }
                )

    sys.addaudithook(audit)
    with bind_run_task_composition(composition, physical_data_root=str(data)):
        sb = TidmadSandbox(
            workspace=str(workspace), run_name="cpu", progress_bar=False, file_index=0
        )
        train = sb.execute_training(
            "cpu", "cpu", model, mc, tc, lc, train_base_seed=17, task_scopes=scopes
        )
        assert train["status"] == "success", train
        assert len(train["results"]["loss_history"]) == 1
        inf = sb.execute_inference(
            "cpu", "cpu", model, mc, lc, inference_batch=2, task_scopes=scopes
        )
        assert inf["status"] == "success", inf
        score = sb.execute_scoring("cpu", "cpu", model, mc, tc, lc, task_scopes=scopes)
        assert score["status"] == "success", score
    scores = np.asarray(
        composition.task_data_path.read_evaluation_payload(
            EvaluationReadRequest(
                deliverable_dir=str(workspace),
                model_type=model,
                run_name="cpu",
                exp_id="cpu",
            )
        ),
        float,
    )
    labels = np.asarray(ev.labels, int)
    assert (
        scores.size == 4
        and np.all(np.isfinite(scores))
        and np.all((scores >= 0) & (scores <= 1))
    )
    assert len(np.unique(tr.labels)) == len(np.unique(ev.labels)) == 2
    pos, neg = scores[labels == 1], scores[labels == 0]
    auc = (
        sum(x > y for x in pos for y in neg)
        + 0.5 * sum(x == y for x in pos for y in neg)
    ) / (len(pos) * len(neg))
    metric = score["results"]["metric_result"]
    assert (
        metric["direction"] == "higher"
        and math.isclose(metric["scalar"], auc, rel_tol=1e-6)
        and composition.task_health_binding is HealthBindingState.EXPLICIT_NONE
    )
    core = Path(sys.modules["core"].__file__).resolve()
    assert core.is_relative_to(Path(sys.prefix).resolve())
    for command in commands:
        argv = command["target_argv"]
        if Path(argv[1]).name == "denoising_score_single.py":
            assert argv[argv.index("--raw_data_dir") + 1] == str(data)
            assert argv[argv.index("--data_dir") + 1] == str(workspace)
        else:
            assert argv[argv.index("--data_dir") + 1] == str(data)
    assert metric["metric_id"] == "energy_matched_roc_auc"
    assert (
        len(commands) == 3
        and [Path(c["target_argv"][1]).name for c in commands]
        == [
            "train_engine_sandbox.py",
            "inference_single.py",
            "denoising_score_single.py",
        ]
        and all(
            c["executable"] == sys.executable
            and Path(c["target_argv"][1]).resolve().is_relative_to(core.parent.parent)
            and (
                "--data_dir" in c["target_argv"] or "--raw_data_dir" in c["target_argv"]
            )
            for c in commands
        )
    )
    return {
        "interpreter": sys.executable,
        "prefix": sys.prefix,
        "core_file": str(core),
        "manifest": str(manifest),
        "data_dir": str(data),
        "train_scope": scopes.training.model_dump(),
        "eval_scope": scopes.evaluation.model_dump(),
        "train_count": 4,
        "eval_count": 4,
        "commands": commands,
        "independent_roc_auc": auc,
        "metric": metric,
        "checkpoint": list(map(str, (workspace / "cached_models").glob("*.pth"))),
        "deliverables": list(map(str, workspace.glob("predictions_*.csv"))),
        "train_ids": list(map(int, tr.event_ids)),
        "eval_ids": list(map(int, ev.event_ids)),
        "train_labels": list(map(int, tr.labels)),
        "eval_labels": list(map(int, ev.labels)),
    }, [
        {"name": "training", "status": train["status"]},
        {"name": "inference", "status": inf["status"]},
        {"name": "scoring", "status": score["status"]},
    ]


def verify_and_receipt(task, exp, workspace, data):
    receipt, phases = run_phases(task, exp, workspace, data)
    receipt["task"] = task
    receipt["phases"] = phases
    assert receipt["checkpoint"] and receipt["deliverables"]
    (workspace / "cpu_witness_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    print(json.dumps(receipt, indent=2))


def main():
    exp = Path(sys.argv[1]).resolve()
    assert Path(sys.prefix).resolve() == exp / ".venv"
    from core.generated_library import bind_generated_library_to_workspace

    bind_generated_library_to_workspace(str(Path(sys.argv[3]).resolve()))
    verify_and_receipt(
        sys.argv[2], exp, Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve()
    )


if __name__ == "__main__":
    main()
