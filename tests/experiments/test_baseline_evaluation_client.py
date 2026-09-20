"""Real subprocess transport distinguishes feedback, wrong receipts and failures."""

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from execute_tools.evaluation_execution import CandidateEvaluationRequest
from execute_tools.evaluation_metric import NotScoreableResult

from experiments.tidmad.main_orchestrator.baseline_evaluation import (
    BaselineCandidateEvaluator,
    BaselineEvaluationSettings,
)

ROOT = Path(__file__).resolve().parents[2]


def _client(tmp_path, mode):
    roots = {
        name: str(tmp_path / name) for name in ("archive", "feedback", "candidates")
    }
    cfg = tmp_path / "settings.json"
    cfg.write_text(json.dumps({**roots, "mode": mode, "checkout": str(ROOT)}))
    command = tmp_path / "scorer.py"
    command.write_text("""import argparse,json,os,sys
from pathlib import Path
settings=json.loads(Path(sys.argv.pop(1)).read_text())
sys.path.insert(0,settings["checkout"])
from deployments.tidmad_coding_agent_baseline.tools.archive_candidate import candidate_tree_digest
p=argparse.ArgumentParser()
p.add_argument('--band');p.add_argument('--candidate-id');p.add_argument('--candidate-source')
a=p.parse_args();mode=settings['mode'];eligible=mode not in ('invalid','nonfinite')
r={'scalar':float('-inf') if mode=='nonfinite' else 1.5,
'file_vector':[1.0]*4+[None]*16,'scoreable':mode!='nonfinite',
'valid':eligible,'evaluation_split':'official-validation','evaluation_scope':'complete-band',
'candidate_tree_sha256':candidate_tree_digest(Path(a.candidate_source)),
'run_id':os.environ['BASELINE_RUN_ID'],'invocation_id':os.environ['BASELINE_INVOCATION_ID'],
'health_status':'valid' if eligible else 'invalid','health_passed':eligible,
'health_gate_results':[],'health_effective_config_sha256':'b'*64,'eligible_for_selection':eligible,
'sample_set':{str(i):list(range(200)) for i in range(4)}}
if mode=='stale':r['invocation_id']='old'
if mode=='bytes':r['candidate_tree_sha256']='c'*64
if mode=='band':r['file_vector']=[None]*4+[1.0]*6+[None]*10
base=Path(settings['archive'])/a.band/a.candidate_id
output=base if eligible else Path(settings['feedback'])/a.band/(a.candidate_id+'.json')
score=output/'score.json' if eligible else output
score.parent.mkdir(parents=True);score.write_text(json.dumps(r));score.chmod(0o440)
print('/unrelated/receipt' if mode=='path' else output)
""")
    metric = ROOT / "tasks/tidmad/resolved/metric_spec.json"
    settings = BaselineEvaluationSettings(
        band="0-3",
        command=(sys.executable, str(command), str(cfg)),
        archive_root=Path(roots["archive"]),
        evaluation_root=Path(roots["feedback"]),
        candidate_root=Path(roots["candidates"]),
        run_id="test-run",
        evaluator_uid=os.getuid(),
        metric_declaration=metric,
        metric_declaration_sha256=hashlib.sha256(metric.read_bytes()).hexdigest(),
    )

    def export(request, destination):
        destination.mkdir()
        for name in (
            "architecture.json",
            "train_config.json",
            "model.py",
            "model.pt",
            "weights.pth",
        ):
            (destination / name).write_bytes(b"synthetic transport artifact")

    client = BaselineCandidateEvaluator(settings, export)
    request = CandidateEvaluationRequest(
        run_name="run",
        exp_id="attempt",
        model_type="synthetic",
        workspace=str(tmp_path),
        models_dir=str(tmp_path / "models"),
        model_configuration={},
        training_configuration={},
        requested_scope={"sample_set": {"0": [0]}},
        metric=client.metric,
        is_trial=True,
    )
    return client, request


@pytest.mark.parametrize("mode", ["valid", "invalid", "nonfinite"])
def test_actual_subprocess_feedback_preserves_scope_and_eligibility(tmp_path, mode):
    client, request = _client(tmp_path, mode)
    result = client.evaluate(request)
    assert result.eligible_for_selection is (mode == "valid")
    assert result.requested_scope == {"sample_set": {"0": [0]}}
    assert len(result.evaluated_scope["sample_set"]["3"]) == 200
    assert Path(result.receipt_path).is_file()
    if mode == "nonfinite":
        assert isinstance(result.metric, NotScoreableResult)
    else:
        assert result.metric.scalar == 1.5
    assert ("score.json" in result.receipt_path) is (mode == "valid")


@pytest.mark.parametrize("mode", ["stale", "bytes", "band", "path"])
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
