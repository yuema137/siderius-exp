"""What the published manifest may and may not contain.

Reading the overlay is not enough — the TESS pack's own scoreability defect
composed cleanly per entry and failed only when the whole manifest was
resolved. So these cases compose it for real.

* ``test_the_published_manifest_carries_no_scoring_arithmetic`` — the
  boundary as a census over the published bytes. A future edit that keeps a
  secondary metric, or restores the implementation, republishes
  `runtime/scoring.py` to an external caller, and every other check here
  would still pass.
* ``test_the_caller_cannot_score_without_a_bound_evaluator`` — the mechanism
  behind that census. Substituting a real `EvaluationMetric` would give the
  caller working arithmetic, and the composition would look healthier, not
  worse.
* ``test_the_public_path_declares_its_own_identity`` — reusing the pack's id
  gives the framework two implementations under one identity.
* ``test_the_declaration_survives`` — the other half: strip too much and the
  caller no longer knows which metric it optimises or in which direction,
  which fails much later and much less clearly.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
import yaml
from execute_tools.evaluation_metric import CandidateEvaluationMetric
from workflows.task_composition import compose_run_task_bindings

from experiments.phyts_tess.main_orchestrator.public_composition import (
    public_composition,
    write_public_composition,
)
from experiments.phyts_tess.main_orchestrator.public_data_path import (
    PUBLIC_TESS_TASK_ID,
)

EXP_ROOT = Path(__file__).resolve().parents[2]
IDENTITY = ("split", "gaia_id", "tic", "sector")


def _agent_view(tmp_path: Path) -> Path:
    """The two manifests `build_views.py` writes; enough to compose."""
    agent = tmp_path / "agent" / "manifests"
    agent.mkdir(parents=True)
    with (agent / "train.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*IDENTITY, "frot", "frot_err"])
        writer.writeheader()
        writer.writerow(
            {
                "split": "train",
                "gaia_id": "1",
                "tic": "2",
                "sector": "20",
                "frot": "0.5",
                "frot_err": "0.01",
            }
        )
    with (agent / "predict.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(IDENTITY))
        writer.writeheader()
        writer.writerow({"split": "val", "gaia_id": "3", "tic": "4", "sector": "21"})
    return agent.parent


@pytest.fixture
def published(tmp_path):
    destination = tmp_path / "composition.yaml"
    write_public_composition(EXP_ROOT, _agent_view(tmp_path), destination)
    return destination


def test_the_published_manifest_carries_no_scoring_arithmetic(published):
    """A census over the bytes an external caller actually receives."""
    text = published.read_text(encoding="utf-8")
    assert "runtime/scoring.py" not in text, (
        "the published manifest references the task's scoring implementation; "
        "an external caller must receive the metric's declaration, not its "
        "arithmetic"
    )
    payload = yaml.safe_load(text)
    assert "secondary_metrics" not in payload
    assert payload["data_analysis"] == {"enabled": False}

    # The format validator does cross, deliberately: it carries no truth and a
    # caller that cannot check well-formedness submits malformed deliverables.
    assert "scoreability.py" in text


def test_the_caller_cannot_score_without_a_bound_evaluator(published):
    """Composes for real, then asks the metric to work alone."""
    binding = compose_run_task_bindings(str(published))

    assert isinstance(binding.metric, CandidateEvaluationMetric)
    assert not binding.secondary_metrics

    with pytest.raises(Exception) as excinfo:
        binding.metric.require_executor()
    assert "complete evaluator" in str(excinfo.value)


def test_the_public_path_declares_its_own_identity(published):
    binding = compose_run_task_bindings(str(published))
    assert binding.task_data_path_id == PUBLIC_TESS_TASK_ID
    assert binding.task_data_path_id != "phyts_tess_rotation"


def test_the_declaration_survives(published):
    """The caller must still know what it optimises, and which way is better."""
    binding = compose_run_task_bindings(str(published))
    assert binding.metric.spec.id == "r2"
    assert binding.metric.spec.direction == "higher"
    assert binding.task_health_binding is not None
    assert list(binding.model_plugins.required_model_types) == ["tess_reference_cnn"]


def test_every_manifest_reference_is_absolute(tmp_path):
    """The published manifest lives outside the pack; a relative path there
    resolves against the wrong directory, silently, and only at compose time.
    """
    payload = public_composition(EXP_ROOT, _agent_view(tmp_path))

    relative: list[str] = []

    def walk(node: object, trail: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if (
                    key in {"file", "config", "declaration", "dir"}
                    and isinstance(value, str)
                    and not Path(value).is_absolute()
                ):
                    relative.append(f"{trail}{key}={value}")
                else:
                    walk(value, f"{trail}{key}.")
        elif isinstance(node, list):
            for item in node:
                walk(item, trail)

    walk(payload)
    assert not relative, f"relative references survive publication: {relative}"
