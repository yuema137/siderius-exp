"""Executable ownership witnesses for the task-local TIDMAD metric handle."""

from __future__ import annotations

from pathlib import Path

from execute_tools.evaluation_metric import MetricResult, MetricSpec, PresenceScoreabilityContract

from tasks.tidmad.runtime import scoring


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
