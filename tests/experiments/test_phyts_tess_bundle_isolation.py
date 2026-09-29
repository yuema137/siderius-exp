"""The bundle must work without the repository, and without the answers.

This is the property the whole condition rests on, and it is the one that
reading cannot settle: the published manifest resolves absolute paths, and
until the bundle was actually produced those paths pointed back into
siderius-exp — a repository that carries the scoring arithmetic and the
identity manifest. A caller needing that repository is a caller holding the
answers.

So the case composes the published manifest in a **subprocess whose only
addition to the path is the bundle**, then asserts that what it loaded came
from the bundle rather than from the working copy that produced it.

* ``test_the_caller_view_composes_without_the_repository`` — the property.
* ``test_the_caller_view_withholds_the_answers`` — the other half: a bundle
  that composes because it shipped everything would pass the first case.
* ``test_the_export_refuses_a_drifting_task_tree`` — a snapshot taken from
  uncommitted work cannot be reproduced from the revision it records.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from experiments.phyts_tess.main_orchestrator.public_composition import (
    public_composition,
)
from experiments.phyts_tess.main_orchestrator.public_task_tree import (
    EVALUATOR_ONLY_FILES,
    export_task_views,
    prune_bytecode,
)

EXP_ROOT = Path(__file__).resolve().parents[2]

#: Composed in a child process, so the parent's already-imported `tasks`
#: package cannot satisfy the import under test.
_PROBE = """
import inspect, json, sys
from workflows.task_composition import compose_run_task_bindings
import tasks.phyts_tess.runtime.tess_data_path as pack

binding = compose_run_task_bindings(sys.argv[1])
implementation = getattr(binding, "task_data_path", None)
print(json.dumps({
    "pack_module": pack.__file__,
    # Where the COMPOSITION loaded its implementation from, which is a
    # different question from where this probe's own import resolved.
    "loaded_data_path_file": inspect.getfile(type(implementation)),
    "task_data_path_id": binding.task_data_path_id,
    "metric_type": type(binding.metric).__name__,
    "metric_id": binding.metric.spec.id,
    "direction": binding.metric.spec.direction,
    "secondary_metrics": len(binding.secondary_metrics),
    "health_bound": binding.task_health_binding is not None,
}))
"""


@pytest.fixture(scope="module")
def bundle(tmp_path_factory) -> Path:
    """A caller view plus its composed manifest, from the current tree."""
    root = tmp_path_factory.mktemp("bundle")
    caller, evaluator = root / "caller", root / "evaluator"
    export_task_views(EXP_ROOT, caller, evaluator)

    agent_view = root / "agent"
    (agent_view / "manifests").mkdir(parents=True)
    _write_view(agent_view)

    (caller / "composition.yaml").write_text(
        yaml.safe_dump(public_composition(EXP_ROOT, agent_view, caller)),
        encoding="utf-8",
    )
    return root


def _write_view(agent_view: Path) -> None:
    identity = "split,gaia_id,tic,sector"
    (agent_view / "manifests" / "train.csv").write_text(
        f"{identity},frot,frot_err\ntrain,1,2,20,0.5,0.01\n", encoding="utf-8"
    )
    (agent_view / "manifests" / "predict.csv").write_text(
        f"{identity}\nval,3,4,21\n", encoding="utf-8"
    )


def test_the_caller_view_composes_without_the_repository(bundle):
    """Only the bundle is added to the path; the pack must come from it."""
    caller = bundle / "caller"
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE, str(caller / "composition.yaml")],
        cwd=bundle,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": str(caller),
            "HOME": str(bundle),
        },
        capture_output=True,
        text=True,
        # Not `check=True`: a non-zero exit is the interesting outcome here,
        # and its stderr says which import the bundle failed to satisfy.
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    result = json.loads(completed.stdout.strip().splitlines()[-1])

    assert Path(result["pack_module"]).is_relative_to(caller), (
        f"the child loaded the task package from {result['pack_module']}, which "
        "is outside the bundle; the caller would need repository access"
    )
    assert result["task_data_path_id"] == "phyts_tess_rotation_public"
    assert Path(result["loaded_data_path_file"]).is_relative_to(caller), (
        "the composition loaded its data path implementation from "
        f"{result['loaded_data_path_file']}, outside the bundle"
    )
    assert result["metric_type"] == "CandidateEvaluationMetric"
    assert result["metric_id"] == "r2"
    assert result["direction"] == "higher"
    assert result["secondary_metrics"] == 0
    assert result["health_bound"] is True


def test_no_published_reference_points_outside_the_bundle(bundle):
    """Import isolation is only half of it.

    The child can still read a repository file by absolute path, so the
    manifest must not name one. This is the half the subprocess cannot see:
    a manifest pointing back at siderius-exp composes perfectly well on a
    machine that has siderius-exp.
    """
    caller = bundle / "caller"
    payload = yaml.safe_load((caller / "composition.yaml").read_text(encoding="utf-8"))

    outside: list[str] = []

    def walk(node: object, trail: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"file", "config", "declaration", "dir"} and isinstance(
                    value, str
                ):
                    path = Path(value)
                    if path.is_relative_to(EXP_ROOT):
                        outside.append(f"{trail}{key}={value}")
                else:
                    walk(value, f"{trail}{key}.")
        elif isinstance(node, list):
            for item in node:
                walk(item, trail)

    walk(payload)
    assert not outside, (
        "the published manifest points back into siderius-exp, so the caller "
        f"would need the repository that holds the answers: {outside}"
    )


def test_the_caller_view_withholds_the_answers(bundle):
    """A bundle that shipped everything would compose just as happily."""
    caller, evaluator = bundle / "caller", bundle / "evaluator"
    for withheld in EVALUATOR_ONLY_FILES:
        assert not (caller / withheld).exists(), f"{withheld} reached the caller"
        assert (evaluator / withheld).exists(), (
            f"{withheld} is in neither view; the evaluator cannot score without it"
        )

    # No stray bytecode carrying this machine's paths.
    assert not list(caller.rglob("__pycache__")) or prune_bytecode(caller)


def test_the_export_refuses_a_drifting_task_tree(tmp_path):
    """An uncommitted change under the task package must refuse the snapshot."""
    drifting = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(drifting)], check=True)
    package = drifting / "tasks" / "phyts_tess"
    package.mkdir(parents=True)
    (package / "marker.txt").write_text("uncommitted\n", encoding="utf-8")

    with pytest.raises(ValueError, match="uncommitted"):
        export_task_views(drifting, tmp_path / "public", tmp_path / "evaluator")
