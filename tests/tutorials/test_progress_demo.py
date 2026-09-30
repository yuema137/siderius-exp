"""Preserve invalid raw scores, outer iteration identity and no-relaunch behavior."""

import json

import matplotlib
import pytest

matplotlib.use("Agg")

from tutorials.paper.progress import plot_progress, read_progress
from tutorials.paper.project import create_project
from tutorials.paper.quick_demo import prepare_demo, run_demo


def write_record(workspace, *, iteration=2, score=-0.4, status="success", health=False):
    path = (
        workspace
        / f"iter_{iteration:03d}"
        / "iteration_001"
        / "model"
        / "run_output_iter_001.json"
    )
    path.parent.mkdir(parents=True)
    gate = {
        "gate_name": "dispersion",
        "execution_status": "passed" if health else "failed",
        "check_passed": health,
        "would_invalidate_under_production_policy": False,
        "resolved_action": "continue",
    }
    record = {
        "exp_id": "model_formal",
        "status": status,
        "model_type": "model",
        "timestamp": "2026-09-29T00:00:00Z",
        "params": {},
        "is_trial": False,
        "logical_round": 3,
        "denoising_score": None,
        "metric_result": {"metric_id": "r2", "direction": "higher", "scalar": score},
        "health_gate_results": [gate],
    }
    output = {
        "run_name": "iter_001",
        "model_type": "model",
        "file_index": 0,
        "status": "completed",
        "completed_rounds": 3,
        "total_attempts": 2,
        "started_at": "2026-09-29T00:00:00Z",
        "finished_at": "2026-09-29T00:01:00Z",
        "all_records": [{**record, "exp_id": "model_trial", "is_trial": True}, record],
    }
    path.write_text(json.dumps(output))
    return path


def test_plot_preserves_invalid_raw_score_and_outer_iteration(tmp_path):
    workspace = tmp_path / "run"
    write_record(workspace, status="failed_mode_collapse")
    points = read_progress(workspace)
    assert len(points) == 1
    assert points[0].iteration == 2  # Not inner iteration_001 or logical_round=3.
    assert points[0].score == -0.4  # Raw metric survives accepted-score penalty.
    assert points[0].validity == "fail"
    fig = plot_progress(
        workspace, tmp_path / "plots", title="test", expected_iterations=3
    )
    assert list(fig.axes[0].collections[0].get_facecolors()[0]) == [1, 1, 1, 1]
    assert (
        fig.axes[0].collections[0].get_offsets()[0, 1] == 0
    )  # Paper boundary triangle; CSV retains -0.4.
    assert (tmp_path / "plots/score-versus-iteration.csv").is_file()


def test_no_score_is_not_fabricated_zero_and_health_unknown_is_not_pass(tmp_path):
    workspace = tmp_path / "run"
    p = write_record(workspace, score=None)
    fig = plot_progress(workspace, tmp_path / "plots", title="missing")
    assert len(fig.axes[0].collections) == 0
    assert len(fig.axes) == 1  # No extra diagnostic strip.
    d = json.loads(p.read_text())
    d["all_records"][1]["metric_result"]["scalar"] = 0.7
    d["all_records"][1]["denoising_score"] = 0.7
    d["all_records"][1]["health_gate_results"] = []
    p.write_text(json.dumps(d))
    assert read_progress(workspace)[0].validity == "unknown"


def test_completed_demo_reuses_records_and_changed_settings_require_new_name(
    tmp_path, monkeypatch
):
    project = tmp_path / "project"
    create_project(project, tmp_path / "infra")
    files = prepare_demo(project, "tess", name="quick", settings={"iterations": 3})
    import hashlib

    files.completion.write_text(
        json.dumps(
            {
                "experiment_sha256": hashlib.sha256(
                    files.experiment.read_bytes()
                ).hexdigest(),
                "exit_code": 0,
            }
        )
    )
    monkeypatch.setattr(
        "subprocess.Popen", lambda *a, **k: pytest.fail("completed demo relaunched")
    )
    assert run_demo(files)["exit_code"] == 0
    with pytest.raises(ValueError, match="different saved settings"):
        prepare_demo(project, "tess", name="quick", settings={"iterations": 4})


def test_task_score_is_not_clipped_to_r2_axis(tmp_path):
    workspace = tmp_path / "run"
    path = write_record(workspace, score=-10.2, status="failed_mode_collapse")
    data = json.loads(path.read_text())
    for record in data["all_records"]:
        record["metric_result"]["metric_id"] = "tidmad_denoising_score"
    path.write_text(json.dumps(data))
    fig = plot_progress(workspace, tmp_path / "plots", title="TIDMAD")
    assert fig.axes[0].collections[0].get_offsets()[0, 1] == -10.2
    assert fig.axes[0].get_ylim()[0] < -10.2 < fig.axes[0].get_ylim()[1]


def test_explicit_no_health_task_plots_success_without_inventing_health_result(
    tmp_path,
):
    """Missing checks are unknown by default; an explicit no-Health task is different."""
    workspace = tmp_path / "run"
    path = write_record(workspace, score=0.4)
    data = json.loads(path.read_text())
    data["all_records"][1]["health_gate_results"] = []
    for record in data["all_records"]:
        record["denoising_score"] = 0.4
    path.write_text(json.dumps(data))
    assert read_progress(workspace)[0].validity == "unknown"
    assert read_progress(workspace, health_policy="none")[0].validity == "pass"
    data["all_records"][1]["status"] = "failed_mode_collapse"
    path.write_text(json.dumps(data))
    assert read_progress(workspace, health_policy="none")[0].validity == "fail"
