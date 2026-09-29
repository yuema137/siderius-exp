"""The caller-side evaluator over a real subprocess boundary.

Mirrors ``test_baseline_evaluation_client.py``. A fake `tess-score` writes
receipts in named modes so each projection and each refusal is reached by
the same transport the real wrapper uses.

* ``test_receipt_projection_preserves_scope_and_eligibility`` — valid,
  Health-invalid and not-scoreable receipts each project to the typed
  result the tuner reads, with the evaluated scope carried through.
* ``test_wrong_receipt_cannot_be_accepted`` — a receipt for another
  invocation, other candidate bytes, an incomplete split or an unrelated
  path is refused before any projection.
* ``test_metric_mismatch_fails_before_export_or_scoring``
* ``test_scorer_failure_preserves_diagnostic_and_trained_candidate``
* ``test_exporter_round_trip_sets_aside_what_the_scorer_would_refuse`` —
  an export whose forward violates the contract is renamed, never deleted,
  and never handed to the scorer.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from execute_tools.evaluation_execution import CandidateEvaluationRequest
from execute_tools.evaluation_metric import MetricResult, NotScoreableResult

from experiments.phyts_tess.main_orchestrator import tess_evaluation as module
from experiments.phyts_tess.main_orchestrator.candidate_model import (
    REQUIRED_CANDIDATE_FILES,
    candidate_tree_digest,
)
from experiments.phyts_tess.main_orchestrator.tess_evaluation import (
    TessCandidateEvaluator,
    TessEvaluationSettings,
    TessNativeExporter,
)
from tests.experiments.test_phyts_tess_candidate_model import Linear, write_candidate

EXP_ROOT = Path(__file__).resolve().parents[2]
METRIC = EXP_ROOT / "tasks/phyts_tess/declared/metric_r2.json"

_FAKE_SCORER = """import argparse, json, sys
from pathlib import Path
settings = json.loads(Path(sys.argv.pop(1)).read_text())
p = argparse.ArgumentParser()
p.add_argument('--candidate-source'); p.add_argument('--candidate-id'); p.add_argument('--run-id')
a = p.parse_args(); mode = settings['mode']
scoreable = mode != 'nonfinite'; healthy = mode not in ('invalid', 'nonfinite')
gate = {'gate_name': 'phyts_tess_prediction_dispersion', 'execution_status': 'passed' if healthy else 'failed',
        'check_passed': healthy, 'would_invalidate_under_production_policy': not healthy,
        'resolved_action': 'continue' if healthy else 'invalidate_round',
        'failure_reason': None if healthy else 'sample dispersion 0.001 below floor 0.05'}
r = {'version': 'phyts-tess-orchestration-score-v1', 'scalar': 0.75 if scoreable else None,
     'scoreable': scoreable, 'valid': scoreable and healthy, 'evaluation_split': 'val',
     'evaluation_scope': 'complete-split', 'evaluated_rows': 442, 'declared_rows': 442,
     'candidate_tree_sha256': settings['digest'], 'run_id': a.run_id, 'invocation_id': a.candidate_id,
     'health_status': 'valid' if healthy else 'invalid', 'health_passed': healthy,
     'health_gate_results': [gate], 'health_effective_config_sha256': 'b' * 64,
     'eligible_for_selection': scoreable and healthy,
     'secondary_results': [{'metric_id': 'rmse', 'direction': 'lower', 'scalar': 0.3}] if scoreable else []}
if mode == 'stale': r['invocation_id'] = 'orchestration-old'
if mode == 'bytes': r['candidate_tree_sha256'] = 'c' * 64
if mode == 'rows': r['evaluated_rows'] = 441
out = Path(settings['evaluation_root']) / (a.candidate_id + '.json')
out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(r)); out.chmod(0o444)
print('/unrelated/receipt.json' if mode == 'path' else out)
"""


def _export(request: CandidateEvaluationRequest, destination: Path) -> None:
    """Deterministic bytes, so the fake scorer can be told the digest up front."""
    destination.mkdir()
    for name in REQUIRED_CANDIDATE_FILES:
        (destination / name).write_bytes(b"synthetic transport artifact")


def _client(
    tmp_path: Path, mode: str
) -> tuple[TessCandidateEvaluator, CandidateEvaluationRequest]:
    _export(None, tmp_path / "digest-probe")  # type: ignore[arg-type]
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "mode": mode,
                "evaluation_root": str(tmp_path / "evaluations"),
                "digest": candidate_tree_digest(tmp_path / "digest-probe"),
            }
        )
    )
    scorer = tmp_path / "scorer.py"
    scorer.write_text(_FAKE_SCORER)
    settings = TessEvaluationSettings(
        command=(sys.executable, str(scorer), str(settings_path)),
        candidate_root=tmp_path / "candidates",
        evaluation_root=tmp_path / "evaluations",
        run_id="test-run",
        metric_declaration=METRIC,
        metric_declaration_sha256=hashlib.sha256(METRIC.read_bytes()).hexdigest(),
        evaluator_uid=os.getuid(),
    )
    client = TessCandidateEvaluator(settings, _export)
    request = CandidateEvaluationRequest(
        run_name="run",
        exp_id="attempt",
        model_type="synthetic",
        workspace=str(tmp_path / "workspace"),
        models_dir=str(tmp_path / "models"),
        model_configuration={},
        training_configuration={},
        requested_scope={"split": "val", "portion": 1.0},
        metric=client.metric,
        is_trial=False,
    )
    return client, request


@pytest.mark.parametrize("mode", ["valid", "invalid", "nonfinite"])
def test_receipt_projection_preserves_scope_and_eligibility(tmp_path, mode):
    client, request = _client(tmp_path, mode)

    result = client.evaluate(request)

    assert result.eligible_for_selection is (mode == "valid")
    assert result.requested_scope == {"split": "val", "portion": 1.0}
    assert result.evaluated_scope == {
        "split": "val",
        "scope": "complete-split",
        "rows": 442,
    }
    assert Path(result.receipt_path).is_file()
    assert result.health_gate_results[0].gate_name == "phyts_tess_prediction_dispersion"
    if mode == "nonfinite":
        assert isinstance(result.metric, NotScoreableResult)
        assert result.secondary_results == ()
    else:
        assert isinstance(result.metric, MetricResult)
        assert result.metric.scalar == 0.75
        assert result.secondary_results[0].metric_id == "rmse"
    if mode == "invalid":
        assert result.health_status == "invalid"
        assert result.failure_reason == "sample dispersion 0.001 below floor 0.05"


@pytest.mark.parametrize("mode", ["stale", "bytes", "rows", "path"])
def test_wrong_receipt_cannot_be_accepted(tmp_path, mode):
    client, request = _client(tmp_path, mode)
    with pytest.raises(ValueError):
        client.evaluate(request)


def test_metric_mismatch_fails_before_export_or_scoring(tmp_path):
    client, request = _client(tmp_path, "valid")
    wrong = request.model_copy(
        update={"metric": request.metric.model_copy(update={"direction": "lower"})}
    )
    with pytest.raises(ValueError, match="frozen evaluator declaration"):
        client.evaluate(wrong)
    assert not client.settings.candidate_root.exists()


def test_scorer_failure_preserves_diagnostic_and_trained_candidate(tmp_path):
    client, request = _client(tmp_path, "valid")
    Path(client.settings.command[1]).write_text(
        "import sys\nprint('model device mismatch: cpu versus cuda', file=sys.stderr)\n"
        "raise SystemExit(7)\n"
    )
    with pytest.raises(RuntimeError, match="model device mismatch") as failure:
        client.evaluate(request)
    candidate = next(p for p in client.settings.candidate_root.iterdir() if p.is_dir())
    assert (candidate / "model.pt").is_file()
    assert str(candidate) in str(failure.value)
    diagnostic = json.loads(
        next(
            (Path(request.workspace) / "evaluation_diagnostics").glob("*.json")
        ).read_text()
    )
    assert diagnostic["returncode"] == 7
    assert "model device mismatch" in diagnostic["stderr"]
    assert diagnostic["candidate_sha256"] == candidate_tree_digest(candidate)


@pytest.mark.parametrize("outputs", [1, 2])
def test_exporter_round_trip_sets_aside_what_the_scorer_would_refuse(
    tmp_path, monkeypatch, outputs
):
    """The exporter's own check is the scorer's loader on the scorer's contract.

    With `outputs=1` the export completes and carries `contract.json`; with
    `outputs=2` the forward violates the contract, the directory is renamed
    aside (never removed) and the error reaches the caller.
    """

    def fake_native_export(
        request, destination, *, examples, method, execution_devices
    ):
        write_candidate(destination, Linear(out=outputs))
        (destination / "contract.json").unlink()

    monkeypatch.setattr(module, "export_native_model", fake_native_export)
    exporter = TessNativeExporter(inference_batch_size=2)
    destination = tmp_path / "candidate"

    if outputs == 1:
        exporter(None, destination)  # type: ignore[arg-type]
        assert (
            json.loads((destination / "contract.json").read_text())[
                "inference_batch_size"
            ]
            == 2
        )
        return

    with pytest.raises(ValueError, match="one scalar per curve"):
        exporter(None, destination)  # type: ignore[arg-type]
    assert not destination.exists()
    aside = [
        p for p in tmp_path.iterdir() if p.name.startswith("candidate.failed-export-")
    ]
    assert len(aside) == 1 and (aside[0] / "model.pt").is_file()
