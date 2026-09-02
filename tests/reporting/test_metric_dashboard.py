"""Focused tests for the static metric trajectory dashboard."""

from __future__ import annotations

import json
from pathlib import Path

from reporting.metric_dashboard import collect_panel, render_dashboard


def _record(
    workspace: Path,
    iteration: int,
    suffix: str,
    score: float,
    *,
    is_trial: bool,
    gate_action: str = "continue",
) -> None:
    target = (
        workspace
        / f"iter_{iteration:03d}"
        / "iteration"
        / "model"
        / "records"
        / f"iter_{iteration:03d}"
        / f"model_iter_{iteration:03d}_{suffix}.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "exp_id": target.stem,
                "status": "success",
                "is_trial": is_trial,
                "gate_action": gate_action,
                "metric_result": {
                    "metric_id": "auc",
                    "direction": "higher",
                    "scalar": score,
                },
            }
        ),
        encoding="utf-8",
    )


def _run_output(workspace: Path, iteration: int, score: float) -> None:
    target = (
        workspace
        / f"iter_{iteration:03d}"
        / "iteration"
        / "model"
        / f"run_output_iter_{iteration:03d}.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "metric_spec": {"id": "auc", "direction": "higher"},
                "best_valid_formal_denoising_score": score,
                "best_valid_formal_exp_id": f"formal_iter_{iteration:03d}",
                "best_valid_trial_denoising_score": score - 0.1,
                "best_valid_trial_exp_id": f"trial_iter_{iteration:03d}",
            }
        ),
        encoding="utf-8",
    )


def test_formal_current_and_health_valid_cumulative_best(tmp_path: Path) -> None:
    """A refused high score must not become current or cumulative best."""
    workspace = tmp_path / "run"
    _record(workspace, 1, "trial", 0.50, is_trial=True)
    _record(workspace, 1, "formal", 0.55, is_trial=False)
    _record(workspace, 2, "formal", 0.52, is_trial=False)
    _record(
        workspace, 3, "refused", 0.99, is_trial=False, gate_action="invalidate_round"
    )
    _record(workspace, 3, "formal", 0.60, is_trial=False)

    panel = collect_panel("example", workspace)

    assert [point["current"] for point in panel["points"]] == [0.55, 0.52, 0.60]
    assert [point["best"] for point in panel["points"]] == [0.55, 0.55, 0.60]
    assert [point["new_best"] for point in panel["points"]] == [True, False, True]


def test_renderer_is_self_contained_and_labels_both_series(tmp_path: Path) -> None:
    panel = {
        "name": "example",
        "workspace": "/runtime/example",
        "metric_id": "auc",
        "direction": "higher",
        "points": [
            {
                "iteration": 1,
                "current": 0.55,
                "best": 0.55,
                "new_best": True,
                "phase": "formal",
                "exp_id": "model_iter_001_001",
            }
        ],
    }
    output = tmp_path / "dashboard.html"
    render_dashboard([panel], output)
    document = output.read_text(encoding="utf-8")
    assert "cumulative best" in document
    assert "current iteration" in document
    assert "★" in document
    assert "<svg" in document
    assert 'http-equiv="refresh" content="30"' in document
    assert "https://" not in document


def test_iteration_output_is_authority_for_formal_result(tmp_path: Path) -> None:
    workspace = tmp_path / "run"
    _record(workspace, 1, "trial", 0.50, is_trial=True)
    _run_output(workspace, 1, 0.61)

    panel = collect_panel("example", workspace)

    assert panel["points"] == [
        {
            "iteration": 1,
            "current": 0.61,
            "best": 0.61,
            "new_best": True,
            "phase": "formal",
            "exp_id": "formal_iter_001",
        }
    ]
