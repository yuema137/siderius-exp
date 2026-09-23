"""A frozen public task must compose without the private scoring implementation."""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from experiments.tidmad.main_orchestrator.public_composition import (
    public_analysis_composition,
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


def test_full_overlay_composes_with_frozen_analysis_policy(tmp_path):
    from core.generated_library import bind_generated_library_to_workspace
    from execute_tools.analysis_materialization import TaskAnalysisCapability
    from execute_tools.task_registration_scope import run_registration_scope
    from workflows.task_composition import compose_run_task_bindings

    root = Path(__file__).resolve().parents[2]
    band = "10-14"
    from experiments.tidmad.information_treatments.frozen_prior import (
        full_analysis_policy,
    )

    policy = tmp_path / "analysis.yaml"
    policy.write_text(
        yaml.safe_dump(full_analysis_policy(root, band).model_dump(mode="json"))
    )
    manifest = tmp_path / "composition.yaml"
    manifest.write_text(yaml.safe_dump(public_analysis_composition(root, policy)))
    bind_generated_library_to_workspace(tmp_path / "state")
    with run_registration_scope():
        composition = compose_run_task_bindings(str(manifest))
    assert composition.data_analysis is not None
    assert isinstance(composition.task_data_path, TaskAnalysisCapability)
    assert composition.task_data_path.task_data_path_id == "tidmad_frozen_training_pool"
    assert composition.metric.spec.id == "tidmad_denoising_score"


@pytest.mark.parametrize("order", [("training", "analysis"), ("analysis", "training")])
def test_training_and_analysis_share_frozen_plugin_identity(tmp_path, order, monkeypatch):
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    from core.generated_library import bind_generated_library_to_workspace
    from execute_tools.task_registration_scope import run_registration_scope
    from workflows.task_composition import compose_run_task_bindings

    from experiments.tidmad.information_treatments.frozen_prior import (
        full_analysis_policy,
    )

    root = Path(__file__).resolve().parents[2]
    public = tmp_path / "frozen"
    shutil.copytree(
        root / "tasks/tidmad",
        public / "tasks/tidmad",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (public / "tasks/tidmad/runtime/scoring.py").unlink()
    before = {
        str(p.relative_to(public)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in public.rglob("*")
        if p.is_file()
    }
    policy = tmp_path / "analysis-policy.yaml"
    policy.write_text(
        yaml.safe_dump(full_analysis_policy(root, "0-3").model_dump(mode="json"))
    )
    manifests = {}
    for name, payload in {
        "training": public_candidate_composition(public),
        "analysis": public_analysis_composition(public, policy),
    }.items():
        manifests[name] = tmp_path / (name + ".yaml")
        manifests[name].write_text(yaml.safe_dump(payload))
    bind_generated_library_to_workspace(tmp_path / "state")
    with run_registration_scope():
        bindings = {
            name: compose_run_task_bindings(str(manifests[name])) for name in order
        }
        assert bindings["training"].data_analysis is None
        assert bindings["analysis"].data_analysis is not None
        assert (
            bindings["training"].task_data_path._delegate
            is bindings["analysis"].task_data_path
        )
        # Repeated switching must retain the same frozen implementation.
        for name in reversed(order):
            compose_run_task_bindings(str(manifests[name]))
    assert before == {
        str(p.relative_to(public)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in public.rglob("*")
        if p.is_file()
    }
