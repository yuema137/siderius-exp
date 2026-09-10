"""Campaign-owned checks for persisted Gold band and Stage-2 state."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


EXP_ROOT = Path(__file__).resolve().parents[2]
STATE_HELPER = (
    EXP_ROOT / "campaigns" / "tidmad_gold" / "scripts" / "gold_campaign_state.py"
)
METRIC_SPEC = {
    "id": "tidmad_denoising_score",
    "direction": "higher",
    "aggregation": "tidmad_anchor_normalised_linear_grand_mean",
    "transform": "log",
    "transform_params": {"log_base": 5.27},
    "references": ["anchor_map", "raw_baseline", "ground_truth"],
    "scoreability": {
        "contract_id": "tidmad_denoised_h5",
        "input_channel_group": "channel0001",
        "required_attrs": ["voltage_range_mV", "sampling_frequency"],
        "required_storage_dtype": "int8",
    },
}


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    return Path(configured).resolve()


def _run(*args: str, checkout: Path | None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if checkout is None:
        env.pop("SIDERIUS_CHECKOUT", None)
    else:
        env["SIDERIUS_CHECKOUT"] = str(checkout)
    return subprocess.run(
        [sys.executable, str(STATE_HELPER), *args],
        cwd=EXP_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def test_state_helper_uses_the_explicit_framework_checkout(tmp_path: Path) -> None:
    """Catch derivation of a nonexistent framework root from the external script path."""
    workspace = tmp_path / "empty_band"
    output = tmp_path / "state.json"

    completed = _run(
        "band-state",
        "--workspace",
        str(workspace),
        "--horizon",
        "20",
        "--band",
        "0-3",
        "--out",
        str(output),
        checkout=_siderius_checkout(),
    )

    assert completed.returncode == 0, completed.stderr
    state = json.loads(output.read_text(encoding="utf-8"))
    assert state["next_iter"] == 1
    assert state["committed_count"] == 0
    assert state["terminal"] is False


def test_state_helper_refuses_an_implicit_framework_checkout() -> None:
    """Catch silent imports from an ambient or path-derived SIDERIUS clone."""
    completed = _run("--help", checkout=None)

    assert completed.returncode != 0
    assert "SIDERIUS_CHECKOUT" in completed.stderr


def _record(
    exp_id: str,
    score: float,
    *,
    is_trial: object = "absent",
    status: str = "success",
) -> dict[str, object]:
    record: dict[str, object] = {
        "exp_id": exp_id,
        "status": status,
        "model_type": "wavenet",
        "params": {},
        "timestamp": "2026-08-26 00:00:30",
        "denoising_score": score,
        "health_gate_enabled": False,
    }
    if is_trial != "absent":
        record["is_trial"] = is_trial
    return record


def _write_iteration(
    workspace: Path,
    index: int,
    records: list[dict[str, object]],
    *,
    metric_spec: dict[str, object] | None = METRIC_SPEC,
    manifest_status: str = "completed",
    run_name: str = "goldpod_v015_band0-3",
) -> None:
    iteration = workspace / f"iter_{index:03d}"
    output_dir = iteration / "iteration_001" / "wavenet"
    output_dir.mkdir(parents=True)
    output = {
        "run_name": run_name,
        "model_type": "wavenet",
        "file_index": 0,
        "status": "completed",
        "completed_rounds": 1,
        "total_attempts": len(records),
        "best_exp_id": records[0]["exp_id"] if records else "none",
        "best_denoising_score": 0.0,
        "started_at": "2026-08-26 00:00:00",
        "finished_at": "2026-08-26 00:01:00",
        "all_records": records,
    }
    if metric_spec is not None:
        output["metric_spec"] = metric_spec
    output_path = output_dir / f"run_output_{run_name}.json"
    output_path.write_text(json.dumps(output), encoding="utf-8")
    manifest = {
        "status": manifest_status,
        "iteration_dir": str(iteration),
        "output_path": str(output_path),
        "model_name": "wavenet",
    }
    (iteration / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _band_state(
    workspace: Path,
    output: Path,
    *extra: str,
    horizon: int = 20,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    completed = _run(
        "band-state",
        "--workspace",
        str(workspace),
        "--horizon",
        str(horizon),
        "--band",
        "0-3",
        "--out",
        str(output),
        *extra,
        checkout=_siderius_checkout(),
    )
    payload = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    return completed, payload


def test_persisted_formal_roles_select_the_best_formal_candidate(
    tmp_path: Path,
) -> None:
    """Preserve #316 B2: absent and false are Formal; true remains Trial."""
    workspace = tmp_path / "band"
    workspace.mkdir()
    _write_iteration(
        workspace,
        1,
        [
            _record("formal_absent", 2.0),
            _record("formal_false", 3.0, is_trial=False),
            _record("trial_true", 9.0, is_trial=True),
            _record("failed", 10.0, status="error_training"),
        ],
    )

    completed, state = _band_state(workspace, tmp_path / "state.json")

    assert completed.returncode == 0, completed.stderr
    assert state["incumbent"]["exp_id"] == "formal_false"
    assert state["scan"]["formal_success"] == 2


def test_metric_direction_comes_from_each_run_stamp(tmp_path: Path) -> None:
    """Catch an assumed higher-is-better rule in the campaign scanner."""
    workspace = tmp_path / "band"
    workspace.mkdir()
    lower = {**METRIC_SPEC, "direction": "lower"}
    _write_iteration(
        workspace,
        1,
        [_record("higher", 5.0), _record("lower", 2.0)],
        metric_spec=lower,
    )

    completed, state = _band_state(workspace, tmp_path / "state.json")

    assert completed.returncode == 0, completed.stderr
    assert state["incumbent"]["exp_id"] == "lower"
    assert state["incumbent"]["metric_direction"] == "lower"


def test_score_without_metric_stamp_refuses_fail_closed(tmp_path: Path) -> None:
    """Catch comparison of a Formal score whose ordering cannot be known."""
    workspace = tmp_path / "band"
    workspace.mkdir()
    _write_iteration(
        workspace,
        1,
        [_record("formal", 1.0)],
        metric_spec=None,
    )

    completed, state = _band_state(workspace, tmp_path / "state.json")

    assert completed.returncode == 2
    assert not state
    assert "metric_spec" in completed.stderr


def test_stop_rule_and_horizon_are_derived_from_persisted_state(tmp_path: Path) -> None:
    """Catch shell-memory resume state or an assumed FCNet stopping reference."""
    workspace = tmp_path / "band"
    workspace.mkdir()
    _write_iteration(workspace, 1, [_record("formal", -1.2)])
    output = tmp_path / "state.json"

    completed, state = _band_state(workspace, output)
    assert completed.returncode == 0, completed.stderr
    assert state["stop_rule_evaluable"] is False
    assert state["terminal"] is False

    reference = tmp_path / "fcnet.json"
    reference.write_text(json.dumps({"per_band": {"0-3": -3.5}}), encoding="utf-8")
    completed, state = _band_state(
        workspace,
        output,
        "--fcnet-reference-json",
        str(reference),
    )
    assert completed.returncode == 0, completed.stderr
    assert state["stop_rule_satisfied"] is True
    assert state["terminal_reason"] == "stop_rule_satisfied"

    completed, state = _band_state(workspace, output, horizon=1)
    assert completed.returncode == 0, completed.stderr
    assert state["terminal_reason"] == "horizon_exhausted"


def test_failed_first_iteration_requires_force_fresh(tmp_path: Path) -> None:
    """Catch accidental resume over a noncommitted first iteration."""
    workspace = tmp_path / "band"
    workspace.mkdir()
    _write_iteration(workspace, 1, [], manifest_status="failed")

    completed, state = _band_state(workspace, tmp_path / "state.json")

    assert completed.returncode == 0, completed.stderr
    assert state["next_iter"] == 1
    assert state["needs_force_fresh"] is True


def test_incumbent_validity_uses_the_workspaces_pinned_health_roster(
    tmp_path: Path,
) -> None:
    """Preserve F-4: never judge a run against the current checkout's roster."""
    workspace = tmp_path / "band"
    workspace.mkdir()
    gate_id = "run_declared_blocking"
    effective = {
        "health_gates": [
            {
                "id": gate_id,
                "gate_role": "blocking",
                "after_round": "every",
                "short_circuit": True,
                "checks": [{"name": "output_std", "config": {}}],
                "on_pass": {"action": "continue"},
                "on_fail": {"action": "invalidate_round"},
                "reason": "external witness roster",
            }
        ],
        "task_health_binding": "explicit",
    }
    (workspace / "health_checks_effective.yaml").write_text(
        yaml.safe_dump(effective, sort_keys=True),
        encoding="utf-8",
    )

    def record(exp_id: str, score: float, passed: bool) -> dict[str, object]:
        item = _record(exp_id, score)
        item["health_gate_enabled"] = True
        item["health_gate_results"] = [
            {
                "gate_name": gate_id,
                "execution_status": "passed",
                "check_passed": passed,
            }
        ]
        return item

    _write_iteration(
        workspace,
        1,
        [record("failed_run_gate", 9.9, False), record("passed_run_gate", 1.0, True)],
    )

    completed, state = _band_state(workspace, tmp_path / "state.json")

    assert completed.returncode == 0, completed.stderr
    assert state["incumbent"]["exp_id"] == "passed_run_gate"
    assert state["scan"]["formal_success"] == 2
    assert state["scan"]["healthgate_valid"] == 1


def _deliverable_name(run_name: str, index: int) -> str:
    from execute_tools.deliverable_spec import default_deliverable_naming

    return default_deliverable_naming().name(
        model_type="wavenet",
        run_name=run_name,
        exp_id="formal",
        input_identity=index,
    )


def _stage2_unit(tmp_path: Path, band: str, indices: tuple[int, ...]) -> Path:
    unit = tmp_path / "stage2" / f"wavenetA_{band}"
    workspace = unit / "workspace"
    workspace.mkdir(parents=True)
    run_name = f"goldpod_stage2_wavenetA_{band}"
    _write_iteration(
        workspace,
        1,
        [_record("formal", -2.5)],
        run_name=run_name,
    )
    data_dir = workspace / "iter_001" / "iteration_001" / "wavenet" / "data"
    data_dir.mkdir()
    for index in indices:
        (data_dir / _deliverable_name(run_name, index)).write_bytes(b"h5-bytes")
    return unit


def _finalize(unit: Path, band: str) -> subprocess.CompletedProcess[str]:
    return _run(
        "stage2-finalize",
        "--unit-dir",
        str(unit),
        "--design",
        "wavenetA",
        "--target-band",
        band,
        checkout=_siderius_checkout(),
    )


def test_stage2_finalize_is_band_scoped_and_writes_marker_last(tmp_path: Path) -> None:
    """Preserve Q-S3-2: a 4-9 unit copies six files, never all twenty."""
    unit = _stage2_unit(tmp_path, "4-9", tuple(range(20)))

    completed = _finalize(unit, "4-9")

    assert completed.returncode == 0, completed.stderr
    marker = json.loads((unit / "COMPLETE.json").read_text(encoding="utf-8"))
    assert marker["design"] == "wavenetA"
    assert marker["target_band"] == "4-9"
    assert marker["exp_id"] == "formal"
    assert marker["denoising_score"] == -2.5
    assert marker["healthgate_valid"] is True
    assert marker["deliverable_count"] == 6
    assert {path.name for path in (unit / "deliverables").iterdir()} == {
        _deliverable_name("goldpod_stage2_wavenetA_4-9", index)
        for index in (4, 5, 6, 7, 8, 9)
    }


def test_stage2_finalize_refuses_a_missing_band_file_without_marker(
    tmp_path: Path,
) -> None:
    """Catch partial completion being published as an atomic Stage-2 unit."""
    unit = _stage2_unit(tmp_path, "4-9", (4, 5, 6, 8, 9))

    completed = _finalize(unit, "4-9")

    assert completed.returncode == 2
    assert not (unit / "COMPLETE.json").exists()
    assert "band 4-9 file 7" in completed.stderr
    assert "R-RETENTION-1" in completed.stderr
    assert "file 0" not in completed.stderr


def test_stage2_finalize_refuses_an_unknown_band_without_marker(tmp_path: Path) -> None:
    """Catch treating target-band as a label instead of parsed scope authority."""
    unit = _stage2_unit(tmp_path, "4-9", (4, 5, 6, 7, 8, 9))

    completed = _finalize(unit, "banana")

    assert completed.returncode == 2
    assert not (unit / "COMPLETE.json").exists()
    assert "banana" in completed.stderr
