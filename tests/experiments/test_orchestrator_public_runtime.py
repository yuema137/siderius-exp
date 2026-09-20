"""Catch private repository publication and missing public-client dependencies."""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from experiments.tidmad.main_orchestrator.public_composition import (
    public_candidate_composition,
)
from experiments.tidmad.main_orchestrator.public_runtime import publish_public_runtime

ROOT = Path(__file__).resolve().parents[2]


def test_public_runtime_imports_and_composes_without_operator_tree(tmp_path):
    frozen = tmp_path / "frozen"
    shutil.copytree(
        ROOT / "tasks", frozen / "tasks", ignore=shutil.ignore_patterns("__pycache__")
    )
    (frozen / "tasks/tidmad/runtime/scoring.py").unlink()
    before = {
        str(p.relative_to(frozen)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in frozen.rglob("*")
        if p.is_file()
    }
    output = tmp_path / "public"
    receipt = publish_public_runtime(ROOT, frozen, output)
    assert not (output / ".git").exists()
    assert not (output / "experiments/tidmad/main_fixed_workflow/advice.json").exists()
    assert not (output / "experiments/tidmad/information_treatments").exists()
    assert not (output / "tasks/tidmad/runtime/scoring.py").exists()
    assert not (output / ".venv").exists()
    for name, digest in receipt["source_sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    payload = public_candidate_composition(frozen)
    payload["task_data_path"]["file"] = str(
        output / "experiments/tidmad/main_orchestrator/compact_training.py"
    )
    manifest = tmp_path / "composition.yaml"
    manifest.write_text(yaml.safe_dump(payload))
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            """
import importlib, json, runpy, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
for name in json.loads((root / 'public-runtime.json').read_text())['source_sha256']:
    if name.endswith('.py') and not name.endswith('__init__.py'):
        module = importlib.import_module(name[:-3].replace('/', '.'))
        assert Path(module.__file__).is_relative_to(root), module.__file__
from workflows.task_composition import compose_run_task_bindings
from execute_tools.evaluation_metric import CandidateEvaluationMetric
from experiments.shared.scripted_implementation import implement_for_scripted_export
from experiments.shared.scripted_model_export import qualify_scripted_model
assert callable(implement_for_scripted_export) and callable(qualify_scripted_model)
assert (root / "experiments/shared/scripted_implementation.md").is_file()
c = compose_run_task_bindings(sys.argv[2])
assert isinstance(c.metric, CandidateEvaluationMetric)
assert c.data_analysis is None
assert c.task_data_path.task_data_path_id == 'tidmad_compact_frozen_training_pool'
# Invoke an independently required entrypoint, not only the publisher's own
# file list: omitting the native trainer otherwise passes every import above.
sys.argv = ['native_training_entry', '--help']
try:
    runpy.run_module('experiments.shared.native_training_entry', run_name='__main__')
except SystemExit as exc:
    assert exc.code == 0, exc.code
else:
    raise AssertionError('native training parser did not handle --help')
""",
            str(output),
            str(manifest),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert before == {
        str(p.relative_to(frozen)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in frozen.rglob("*")
        if p.is_file()
    }


def test_private_task_tree_is_refused_before_publication(tmp_path):
    with pytest.raises(ValueError, match="without private scorer"):
        publish_public_runtime(ROOT, ROOT, tmp_path / "public")
    assert not (tmp_path / "public").exists()
