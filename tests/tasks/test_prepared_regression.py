"""Prepared array identity, split, sampling, and real inference contracts."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from execute_tools.generic_inference import run_generic_inference
from execute_tools.task_data_path import (
    DeliverableWriteRequest,
    EpochSamplingParams,
    EvalMaterializationParams,
    EvaluationReadRequest,
    ScopeBuildRequest,
    ValidationScopeError,
)

from tasks.shared.prepared_regression import (
    LigoDataPath,
    PredictionArtifact,
    PreparedDeclaration,
    PreparedPredictionScoreability,
    PreparedScope,
    deliverable_name,
)
from tasks.shared.regression_metrics import RegressionR2, RegressionRmse

ROOT = Path(__file__).resolve().parents[2]


def request(portion=1.0, **kwargs):
    return ScopeBuildRequest(
        round_kind="formal", selection_strategy="snapshot", portion=portion, **kwargs
    )


@pytest.fixture
def prepared(tmp_path):
    (tmp_path / "manifest.json").write_text('{"fixture": true}')
    declaration = PreparedDeclaration(
        task_id=LigoDataPath.task_data_path_id,
        manifest_sha256=hashlib.sha256(
            (tmp_path / "manifest.json").read_bytes()
        ).hexdigest(),
        train_count=80,
        validation_count=20,
        channels=2,
        length=8,
        loss_indices=(3, 17),
    )
    path = tmp_path / "declaration.json"
    path.write_text(declaration.model_dump_json())
    for split, count in [("training", 80), ("evaluator/validation", 20)]:
        folder = tmp_path / split
        folder.mkdir(parents=True)
        targets = np.arange(count, dtype=np.float32).reshape(-1, 1)
        np.save(folder / "targets.npy", targets)
        np.save(
            folder / "inputs.npy",
            np.broadcast_to(targets[:, :, None], (count, 2, 8)).copy(),
        )
    return LigoDataPath(str(path)), tmp_path


def test_fixed_loss_subset_and_full_eval_are_seed_independent(prepared):
    adapter, root = prepared
    for seed in (None, 1, 91):
        scope = adapter.build_eval_scope(request(0.1, seed=seed))
        assert tuple(scope.rows) == (3, 17)
        full = adapter.build_eval_scope(request(seed=seed))
        assert full.row_count == 20 and full.selected_rows is None
        assert (
            len(
                adapter.validation_dataset(
                    scope, EvalMaterializationParams(data_dir=str(root))
                )
            )
            == 2
        )
    encoded = adapter.serialize_scope(scope)
    assert "targets" not in encoded and "truth" not in encoded
    assert adapter.serialize_scope(adapter.deserialize_scope(encoded)) == encoded


def test_training_pool_and_epoch_fraction_remain_agent_controlled(prepared):
    adapter, root = prepared
    full = adapter.build_training_scope(request())
    half = adapter.build_training_scope(request(0.5, seed=2))
    assert full.row_count == 80 and half.row_count == 40
    one = adapter.training_dataset(
        half, EpochSamplingParams(data_dir=str(root), train_portion=0.5, epoch_seed=1)
    )
    two = adapter.training_dataset(
        half, EpochSamplingParams(data_dir=str(root), train_portion=0.5, epoch_seed=2)
    )
    assert len(one) == len(two) == 20
    assert set(one.scope.rows) <= set(half.rows)
    assert one.scope.rows != two.scope.rows
    x, y = one[0]
    assert x.shape == (2, 8) and y.shape == (1,)
    assert x[0, 0] == y[0] == one.scope.rows[0]


def test_wrong_split_identity_and_corrupt_shape_are_refused(prepared):
    adapter, root = prepared
    scope = adapter.build_eval_scope(request())
    with pytest.raises(ValidationScopeError):
        adapter.training_dataset(scope, EpochSamplingParams(data_dir=str(root)))
    with pytest.raises(ValueError):
        adapter.deserialize_scope(
            scope.model_copy(update={"declaration_sha256": "other"}).model_dump_json()
        )
    with pytest.raises(ValueError):
        PreparedScope.model_validate({**scope.model_dump(), "split": "test"})
    np.save(root / "evaluator/validation/inputs.npy", np.zeros((19, 2, 8), np.float32))
    with pytest.raises(ValidationScopeError):
        adapter.validation_dataset(scope, EvalMaterializationParams(data_dir=str(root)))


def test_manifest_mismatch_is_refused(prepared):
    adapter, root = prepared
    (root / "manifest.json").write_text('{"fixture": false}')
    with pytest.raises(ValidationScopeError, match="digest"):
        adapter.training_dataset(
            adapter.build_training_scope(request()),
            EpochSamplingParams(data_dir=str(root)),
        )


def test_real_inference_covers_tail_and_global_physical_scores(prepared):
    adapter, root = prepared
    scope = adapter.build_eval_scope(request())

    class Offset(torch.nn.Module):
        def forward(self, x):
            return x[:, :1, 0] + 2

    identity = {"exp_id": "fixture", "run_name": "fixture", "model_type": "offset"}
    outcome = run_generic_inference(
        data_path=adapter,
        task_scope=scope,
        model=Offset().eval(),
        device=torch.device("cpu"),
        data_dir=str(root),
        batch_size=7,
        write_request=DeliverableWriteRequest(output_dir=str(root), **identity),
    )
    assert outcome.samples == 20 and outcome.batches == 3
    read = EvaluationReadRequest(deliverable_dir=str(root), **identity)
    payload = adapter.read_evaluation_payload(read)
    kwargs = {"evaluation_payload": payload, "task_scope": scope, "data_dir": str(root)}
    assert RegressionRmse._compute(None, {}, **kwargs)[0] == 2.0
    assert RegressionR2._compute(None, {}, **kwargs)[0] == pytest.approx(
        1 - 4 / np.var(np.arange(20))
    )
    verdict = PreparedPredictionScoreability().check(
        {0: str(root / deliverable_name(read))}
    )
    assert verdict.scoreable
    payload.pop(scope.keys[-1])
    with pytest.raises(ValueError, match="exactly"):
        RegressionRmse._compute(None, {}, **kwargs)
    payload[scope.keys[-1]] = 21.0
    payload["validation:999"] = 0.0
    with pytest.raises(ValueError, match="exactly"):
        RegressionRmse._compute(None, {}, **kwargs)


@pytest.mark.parametrize("bad", [True, "1.0", float("nan"), float("inf")])
def test_non_numeric_or_nonfinite_predictions_are_refused(bad):
    with pytest.raises(ValueError):
        PredictionArtifact(
            declaration_sha256="fixture",
            split="validation",
            predictions={"validation:0": bad},
        )


def test_duplicate_prediction_ids_are_refused(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"format":"prepared_scalar_predictions_v1","declaration_sha256":"fixture","split":"validation","predictions":{"validation:0":1.0,"validation:0":2.0}}'
    )
    verdict = PreparedPredictionScoreability().check({0: str(path)})
    assert not verdict.scoreable and "duplicate" in verdict.failures[0].detail


@pytest.mark.parametrize(
    "task,train_count,eval_count", [("ligo", 360000, 90000), ("project8", 40000, 5000)]
)
def test_composition_loads_from_unrelated_cwd_and_preserves_populations(
    task, train_count, eval_count, tmp_path
):
    script = """
import sys
from workflows.task_composition import compose_run_task_bindings
from execute_tools.task_data_path import ScopeBuildRequest
c = compose_run_task_bindings(sys.argv[1])
r = ScopeBuildRequest(round_kind="formal", selection_strategy="snapshot", portion=1.0)
a = c.task_data_path
assert a.build_training_scope(r).row_count == int(sys.argv[2])
assert a.build_eval_scope(r).row_count == int(sys.argv[3])
assert a.build_eval_scope(r.model_copy(update={"portion":0.1})).row_count == int(sys.argv[3]) // 10
assert c.metric.spec.direction == "higher"
assert c.metric.spec.id == "r2"
"""
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(ROOT / f"tasks/phyts_{task}/compositions/regression.yaml"),
            str(train_count),
            str(eval_count),
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        timeout=60,
    )


@pytest.mark.parametrize(
    "task,trial,formal,vram,training_scope",
    [("ligo", 10, 30, 16, "agent"), ("project8", 30, 120, 40, "operator")],
)
def test_experiment_renders_independent_eval_and_training_budgets(
    task, trial, formal, vram, training_scope
):
    from experiments.shared.fixed_workflow_config import render_siderius_args

    folder = ROOT / f"experiments/phyts_{task}/main_fixed_workflow"
    args = render_siderius_args(
        folder / "workflow.json", repository_root=ROOT, siderius_checkout=ROOT
    )
    value = lambda flag: args[args.index(flag) + 1]
    assert value("--formal_training_scope_source") == training_scope
    if training_scope == "agent":
        assert "--formal_train_portion" not in args and "--formal_portion" not in args
    else:
        assert float(value("--formal_train_portion")) == 1.0
        assert float(value("--formal_portion")) == 1.0
    assert float(value("--formal_eval_portion")) == 1.0
    assert float(value("--training_validation_portion")) == 0.1
    assert int(value("--max_rounds")) == 2
    assert int(value("--trial_time_budget_minutes")) == trial
    assert int(value("--formal_time_budget_minutes")) == formal
    assert int(value("--formal_vram_budget_gb")) == vram


@pytest.mark.parametrize("task", ["ligo", "project8"])
def test_qualification_does_not_mutate_formal_files_or_disable_literature(
    task, tmp_path
):
    from experiments.shared.prepared_workflow_command import build_command

    checkout = tmp_path / "infra"
    launcher = checkout / "scripts/launch/run_chain.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/bash\nexit 0\n")
    folder = ROOT / f"experiments/phyts_{task}/main_fixed_workflow"
    before = (folder / "workflow.json").read_bytes()
    args = build_command(
        experiment=folder,
        checkout=checkout,
        data=tmp_path / "data",
        workspace=tmp_path / "unit/workspace",
        run_name="qualification",
        qualification=True,
    )
    value = lambda flag: args[args.index(flag) + 1]
    assert value("--num_iterations") == "2"
    assert value("--max_epochs") == "1"
    assert value("--validation_max_train_samples") == "128"
    assert "--runtime_watchdog" in args and "--no-runtime_watchdog" not in args
    assert value("--formal_eval_portion") == "1.0"
    assert value("--training_validation_portion") == "0.1"
    assert "--ml_lit_review_enabled" in args and "--no-data_analysis_enabled" in args
    assert "--advice" not in args and "--validation_fixed_candidate_plan" not in args
    assert (folder / "workflow.json").read_bytes() == before
    assert json.loads(before)["parameters"]["--max_epochs"] == 100
