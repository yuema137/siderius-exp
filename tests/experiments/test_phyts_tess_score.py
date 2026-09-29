"""`tess-score` end to end, through the isolated entry the wrapper fixes.

The scorer runs in a subprocess exactly as the installed wrapper would run
it (`python -I -B entry policy ...`), against a synthetic evaluator view
whose task code is the checkout's own and whose data is six invented
curves. That is the only way to exercise `_bind_task_view`: in-process the
task package is already imported from the checkout, and the scorer is
right to refuse that.

* ``test_scores_the_complete_split_and_publishes_a_readable_receipt`` — the
  R-squared is cross-checked by hand from the same truth and the same
  model, the caller-side reader accepts the coordinator-written receipt
  for the exact candidate bytes, the task's declared Health family ran,
  and everything is retained under the work root.
* ``test_a_non_finite_model_is_refused_by_name_and_still_receipted``
* ``test_a_candidate_outside_the_caller_root_is_refused``
* ``test_a_second_evaluation_of_the_same_identity_is_refused``
* ``test_invocation_without_the_caller_identity_is_refused``
* ``test_verify_evaluator_policy_reads_the_declared_population``
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

from experiments.phyts_tess.main_orchestrator.candidate_model import (
    candidate_tree_digest,
)
from experiments.phyts_tess.main_orchestrator.tess_receipt import (
    TessEvaluationReceipt,
    read_tess_evaluation,
)
from experiments.phyts_tess.main_orchestrator.tess_score import TessEvaluatorPolicy
from experiments.phyts_tess.main_orchestrator.verify_evaluator_policy import (
    verify_evaluator_policy,
)
from tasks.phyts_tess.runtime.tess_data_path import SEQUENCE_LENGTH, normalize_curve
from tests.experiments.test_phyts_tess_candidate_model import Linear, write_candidate

EXP_ROOT = Path(__file__).resolve().parents[2]
ENTRY = EXP_ROOT / "deployments/phyts_tess_orchestration/tess_score_entry.py"
PACK = EXP_ROOT / "tasks/phyts_tess"
COLUMNS = ("split", "gaia_id", "tic", "sector", "frot", "frot_err")
VAL_ROWS = 6


def _rows() -> list[dict[str, str]]:
    train = [
        {
            "split": "train",
            "gaia_id": str(100 + i),
            "tic": str(900 + i),
            "sector": "20",
            "frot": f"{0.5 + i / 10:.4f}",
            "frot_err": "0.01",
        }
        for i in range(4)
    ]
    val = [
        {
            "split": "val",
            "gaia_id": str(200 + i),
            "tic": str(800 + i),
            "sector": "21",
            "frot": f"{1.0 + i * 0.3:.4f}",
            "frot_err": "0.02",
        }
        for i in range(VAL_ROWS)
    ]
    return [*train, *val]


def _flux(key: str) -> np.ndarray:
    seed = int(key.split(":")[0])
    rng = np.random.default_rng(seed)
    length = int(rng.integers(700, 1400))
    return rng.normal(1.0, 0.05, size=length)


def _deployment(tmp_path: Path) -> tuple[Path, TessEvaluatorPolicy]:
    """A synthetic evaluator view built from the checkout's own task code."""
    view = tmp_path / "evaluator"
    pack = view / "tasks" / "phyts_tess"
    for member in ("runtime", "declared", "plugins"):
        shutil.copytree(
            PACK / member, pack / member, ignore=shutil.ignore_patterns("__pycache__")
        )
    for marker in (Path("tasks/__init__.py"), Path("tasks/phyts_tess/__init__.py")):
        shutil.copyfile(EXP_ROOT / marker, view / marker)
    manifest = pack / "data" / "manifests" / "rotation_identity.csv"
    manifest.parent.mkdir(parents=True)
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(_rows())
    profile_path = pack / "declared" / "dataset_profile.json"
    profile = json.loads(profile_path.read_text())
    profile["topology"]["populations"]["val"] = VAL_ROWS
    profile_path.write_text(json.dumps(profile, indent=2))

    data = tmp_path / "rundata"
    data.mkdir()
    keys = [
        f"{row['gaia_id']}:{row['sector']}" for row in _rows() if row["split"] == "val"
    ]
    np.savez(data / "tess_rotation_val.npz", **{key: _flux(key) for key in keys})

    policy = TessEvaluatorPolicy(
        version="phyts-tess-evaluator-policy-v1",
        caller_uid=os.geteuid() + 1,
        coordinator_uid=os.geteuid(),
        evaluator_view=view,
        validation_data=data,
        candidate_root=tmp_path / "candidates",
        work_root=tmp_path / "work",
        evaluation_root=tmp_path / "evaluations",
    )
    (tmp_path / "candidates").mkdir()
    policy_path = tmp_path / "evaluator.json"
    policy_path.write_text(policy.model_dump_json(indent=2))
    policy_path.chmod(0o644)
    return policy_path, policy


def _run(
    policy_path: Path, candidate: Path, candidate_id: str, *, sudo_uid: str | None
):
    env = {key: value for key, value in os.environ.items() if key != "SUDO_UID"}
    if sudo_uid is not None:
        env["SUDO_UID"] = sudo_uid
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(ENTRY),
            str(policy_path),
            "--candidate-source",
            str(candidate),
            "--candidate-id",
            candidate_id,
            "--run-id",
            "run-1",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )


def _hand_r2(model: torch.nn.Module) -> float:
    truth, predicted = [], []
    for row in _rows():
        if row["split"] != "val":
            continue
        curve = normalize_curve(
            _flux(f"{row['gaia_id']}:{row['sector']}"), SEQUENCE_LENGTH
        )
        tensor = torch.from_numpy(np.asarray(curve, dtype=np.float32)).reshape(1, 1, -1)
        with torch.inference_mode():
            predicted.append(float(model(tensor).reshape(-1)[0]))
        truth.append(float(row["frot"]))
    mean = sum(truth) / len(truth)
    total = sum((t - mean) ** 2 for t in truth)
    residual = sum((t - p) ** 2 for t, p in zip(truth, predicted, strict=True))
    return 1.0 - residual / total


def test_scores_the_complete_split_and_publishes_a_readable_receipt(tmp_path):
    policy_path, policy = _deployment(tmp_path)
    model = Linear()
    candidate = write_candidate(policy.candidate_root / "cand-1", model)

    completed = _run(policy_path, candidate, "cand-1", sudo_uid=str(policy.caller_uid))

    assert completed.returncode == 0, completed.stderr[-4000:]
    receipt_path = Path(completed.stdout.strip())
    assert receipt_path == policy.evaluation_root / "cand-1.json"
    # The caller-side reader, with the identity it would hold, accepts it.
    receipt = read_tess_evaluation(
        receipt_path,
        candidate_sha256=candidate_tree_digest(candidate),
        run_id="run-1",
        invocation_id="cand-1",
        owner_uid=os.geteuid(),
    )
    assert receipt.evaluated_rows == receipt.declared_rows == VAL_ROWS
    assert receipt.scalar == pytest.approx(_hand_r2(model), abs=1e-6)
    assert receipt.eligible_for_selection and receipt.health_status == "valid"
    assert [g["gate_name"] for g in receipt.health_gate_results] == [
        "phyts_tess_prediction_dispersion"
    ], "the task's declared Health family must actually have run"
    assert {r["metric_id"] for r in receipt.secondary_results} == {"rmse", "mae"}
    assert stat.S_IMODE(receipt_path.stat().st_mode) == 0o444
    retained = policy.work_root / "candidates" / "cand-1"
    assert (retained / "candidate" / "model.pt").is_file()
    assert (retained / "score.json").is_file()
    assert list(
        (retained / "deliverable").glob(
            "tess_rotation_synthetic_linear_run-1_cand-1.json"
        )
    )


def test_a_non_finite_model_is_refused_by_name_and_still_receipted(tmp_path):
    policy_path, policy = _deployment(tmp_path)
    broken = Linear()
    with torch.no_grad():
        broken.head.weight.fill_(float("nan"))
    candidate = write_candidate(policy.candidate_root / "cand-nan", broken)

    completed = _run(
        policy_path, candidate, "cand-nan", sudo_uid=str(policy.caller_uid)
    )

    assert completed.returncode == 0, completed.stderr[-4000:]
    receipt = TessEvaluationReceipt.model_validate_json(
        Path(completed.stdout.strip()).read_bytes()
    )
    assert receipt.scoreable is False and receipt.scalar is None
    assert receipt.eligible_for_selection is False
    assert receipt.health_status == "invalid" and receipt.health_gate_results == ()
    refusal = receipt.model_extra["metric_refusal"]
    assert "numerical" in json.dumps(refusal)


def test_a_candidate_outside_the_caller_root_is_refused(tmp_path):
    policy_path, policy = _deployment(tmp_path)
    elsewhere = write_candidate(tmp_path / "elsewhere" / "cand-x", Linear())

    completed = _run(policy_path, elsewhere, "cand-x", sudo_uid=str(policy.caller_uid))

    assert completed.returncode != 0
    assert "must remain below" in completed.stderr
    assert not (policy.work_root / "candidates").exists()


def test_a_second_evaluation_of_the_same_identity_is_refused(tmp_path):
    policy_path, policy = _deployment(tmp_path)
    candidate = write_candidate(policy.candidate_root / "cand-1", Linear())
    first = _run(policy_path, candidate, "cand-1", sudo_uid=str(policy.caller_uid))
    assert first.returncode == 0, first.stderr[-4000:]

    second = _run(policy_path, candidate, "cand-1", sudo_uid=str(policy.caller_uid))

    assert second.returncode != 0
    assert "already evaluated" in second.stderr


@pytest.mark.parametrize("sudo_uid", [None, "0"])
def test_invocation_without_the_caller_identity_is_refused(tmp_path, sudo_uid):
    policy_path, policy = _deployment(tmp_path)
    candidate = write_candidate(policy.candidate_root / "cand-1", Linear())

    completed = _run(policy_path, candidate, "cand-1", sudo_uid=sudo_uid)

    assert completed.returncode != 0
    assert "through sudo" in completed.stderr
    assert not policy.evaluation_root.exists()


def test_verify_evaluator_policy_reads_the_declared_population(tmp_path):
    policy_path, _ = _deployment(tmp_path)

    report = verify_evaluator_policy(policy_path)

    assert report["declared_val_rows"] == VAL_ROWS
    same_account = json.loads(policy_path.read_text())
    same_account["caller_uid"] = same_account["coordinator_uid"]
    policy_path.write_text(json.dumps(same_account))
    with pytest.raises(ValueError, match="separate coordinator account"):
        verify_evaluator_policy(policy_path)


def test_a_view_without_the_task_runtime_cannot_score_with_checkout_bytes(tmp_path):
    """The scorer imports the task from the frozen view, and proves it did.

    Without this refusal a view missing its `tasks/` tree would let the
    scorer fall through to whatever the checkout on `sys.path` carries —
    unfrozen bytes scoring a frozen run, silently.
    """
    policy_path, policy = _deployment(tmp_path)
    shutil.move(policy.evaluator_view / "tasks", tmp_path / "tasks.moved-aside")
    candidate = write_candidate(policy.candidate_root / "cand-1", Linear())

    completed = _run(policy_path, candidate, "cand-1", sudo_uid=str(policy.caller_uid))

    assert completed.returncode != 0
    assert "outside the evaluator view" in completed.stderr
    assert not policy.evaluation_root.exists()
