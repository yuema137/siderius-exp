"""A frozen public task must compose without the private scoring implementation."""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from experiments.tidmad.main_orchestrator.public_composition import (
    public_candidate_composition,
)


def test_public_overlay_preserves_frozen_task_and_loads_without_private_score(tmp_path):
    # Fails if the overlay retains the private import, loses relative references,
    # enables analysis by default or edits the frozen scientific declaration.
    root = Path(__file__).resolve().parents[2]
    public = tmp_path / "frozen"
    task = public / "tasks/tidmad"
    shutil.copytree(
        root / "tasks/tidmad", task, ignore=shutil.ignore_patterns("__pycache__")
    )
    (task / "runtime/scoring.py").unlink()
    before = {
        p: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in task.rglob("*")
        if p.is_file()
    }
    manifest = tmp_path / "deployment.yaml"
    manifest.write_text(yaml.safe_dump(public_candidate_composition(public)))
    # One frozen task package per process, as on each deployed band host.
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import sys
import inspect
from execute_tools.evaluation_metric import CandidateEvaluationMetric
from workflows.task_composition import compose_run_task_bindings
composition = compose_run_task_bindings(sys.argv[1])
assert isinstance(composition.metric, CandidateEvaluationMetric)
assert composition.metric.spec.id == "tidmad_denoising_score"
assert composition.data_analysis is None
assert composition.task_data_path.task_data_path_id == 'tidmad_compact_frozen_training_pool'
assert '/frozen/tasks/tidmad/runtime/' in inspect.getfile(type(composition.task_data_path._delegate))
""",
            str(manifest),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before}

    analysis = tmp_path / "analysis.yaml"
    enabled = public_candidate_composition(public, analysis)
    assert enabled.pop("data_analysis") == {"enabled": True, "config": str(analysis)}
    disabled = public_candidate_composition(public)
    disabled.pop("data_analysis")
    assert enabled == disabled
