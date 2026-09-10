"""Executable ownership witnesses for the task-local TIDMAD metric handle."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace

from execute_tools.evaluation_metric import (
    MetricResult,
    MetricSpec,
    PresenceScoreabilityContract,
)
from execute_tools.task_data_path import EvaluationReadRequest, TaskEvaluationPayload

from tasks.tidmad.runtime import scoring
from tasks.tidmad.runtime import tidmad_data_path
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope


def test_composed_metric_uses_the_task_owned_scoreability_contract() -> None:
    """A legacy framework contract with the same id must not shadow the task."""
    from workflows.task_composition import compose_run_task_bindings

    manifest = (
        Path(__file__).resolve().parents[3]
        / "tasks"
        / "tidmad"
        / "compositions"
        / "bounded_qualification.yaml"
    )
    composition = compose_run_task_bindings(str(manifest))

    contract_type = type(composition.metric.spec.scoreability)
    assert (
        Path(inspect.getsourcefile(contract_type) or "").resolve()
        == (manifest.parents[1] / "runtime" / "scoreability.py").resolve()
    )
    assert contract_type.__name__ == "TidmadScoreabilityContract"


def test_task_metric_delegates_once_to_the_frozen_task_scorer(
    monkeypatch, tmp_path: Path
) -> None:
    """A composed TIDMAD metric must execute this package's scoring authority."""
    calls: list[dict[str, object]] = []

    def fake_score_vector(**kwargs):
        calls.append(kwargs)
        return [1.25, None], 2.5

    monkeypatch.setattr(scoring, "score_vector", fake_score_vector)
    deliverable = tmp_path / "prediction.h5"
    deliverable.touch()
    metric = scoring.TidmadDenoisingMetric(
        MetricSpec(
            id="tidmad_denoising_score",
            direction="higher",
            aggregation="tidmad_anchor_normalised_linear_grand_mean",
            references=("anchor_map",),
            scoreability=PresenceScoreabilityContract(),
        )
    )

    outcome = metric.evaluate(
        {0: str(deliverable)},
        data_dir="predictions",
        sample_set={0: [3]},
        anchor_map={"0": [1.0]},
        s_max=1.0,
    )

    assert isinstance(outcome, MetricResult)
    assert outcome.scalar == 2.5
    assert outcome.per_sample == [1.25, None]
    assert outcome.references_used == ("anchor_map",)
    assert calls == [
        {
            "data_dir": "predictions",
            "sample_set": {0: [3]},
            "anchor_map": {"0": [1.0]},
            "s_max": 1.0,
        }
    ]


def test_composed_metric_translates_its_opaque_scope_and_anchor_reference(
    monkeypatch, tmp_path: Path
) -> None:
    """Catches composed TIDMAD reaching the legacy SampleSet=None scorer."""
    calls: list[dict[str, object]] = []

    def fake_score_vector(**kwargs):
        calls.append(kwargs)
        return [0.75], 1.5

    monkeypatch.setattr(scoring, "score_vector", fake_score_vector)
    prediction = tmp_path / "prediction.h5"
    prediction.touch()
    (tmp_path / "segment_anchors.json").write_text(
        json.dumps({"anchors": {"0": [2.0]}, "s_max": 2.0}),
        encoding="utf-8",
    )
    metric = scoring.TidmadDenoisingMetric(
        MetricSpec(
            id="tidmad_denoising_score",
            direction="higher",
            aggregation="tidmad_anchor_normalised_linear_grand_mean",
            references=("anchor_map",),
            scoreability=PresenceScoreabilityContract(),
        )
    )
    scope = TidmadScope(sample_set={0: [3]}, seg_size=40_000)

    outcome = metric.evaluate(
        {0: str(prediction)},
        evaluation_payload={0: str(prediction)},
        task_scope=scope,
        data_dir=str(tmp_path),
    )

    assert isinstance(outcome, MetricResult)
    assert outcome.scalar == 1.5
    assert len(calls) == 1
    call = calls[0]
    assert call["sample_set"] == {0: [3]}
    assert call["anchor_map"] == {"0": [2.0]}
    assert call["s_max"] == 2.0
    assert call["raw_data_dir"] == str(tmp_path)
    assert call["denoised_filename_fn"](0) == str(prediction)


def test_task_reader_names_every_hdf5_artifact_for_scoreability(
    monkeypatch, tmp_path: Path
) -> None:
    """Catches the composed scoring child checking only one TIDMAD file."""

    class Naming:
        @staticmethod
        def input_identity_of(entry: str) -> int | None:
            return int(entry[-8:-3]) if entry.startswith("prediction_") else None

        @staticmethod
        def name(**kwargs) -> str:
            return f"prediction_{kwargs['input_identity']:05d}.h5"

    monkeypatch.setattr(tidmad_data_path, "resolve_dataset_profile", lambda: object())
    monkeypatch.setattr(
        tidmad_data_path,
        "derive_tidmad_deliverable_spec",
        lambda _profile: SimpleNamespace(naming=Naming()),
    )
    for file_index in (2, 7):
        (tmp_path / f"prediction_{file_index:05d}.h5").touch()

    payload = tidmad_data_path.TidmadTaskDataPath().read_evaluation_payload(
        EvaluationReadRequest(
            deliverable_dir=str(tmp_path),
            exp_id="candidate_001",
            run_name="iter_001",
            model_type="model",
        )
    )

    assert isinstance(payload, TaskEvaluationPayload)
    assert payload.value == payload.deliverables
    assert payload.deliverables == {
        2: str(tmp_path / "prediction_00002.h5"),
        7: str(tmp_path / "prediction_00007.h5"),
    }
