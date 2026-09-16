from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from deployments.tidmad_coding_agent_baseline.tools.clear_workspace import (
    _safe_work_root,
    clear_retained_state,
    clear_workspace,
)


def _prepare(root):
    for child in ("input", "harness", "agent", "state", "submission", "logs"):
        (root / child).mkdir(parents=True)
    payload = b"frozen task\n"
    (root / "input" / "task.md").write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    (root / "input" / "bundle.sha256").write_text(f"{digest}  task.md\n")
    (root / "harness" / "keep").write_text("yes")
    for child in ("agent", "state", "submission", "logs"):
        (root / child / "drill-only").write_text("remove")


def test_production_default_is_the_only_accepted_shallow_work_root():
    """The CLI's /work default must be usable without making /var or /tmp safe."""

    assert _safe_work_root(Path("/work")) is True
    assert _safe_work_root(Path("/")) is False
    assert _safe_work_root(Path("/var")) is False
    assert _safe_work_root(Path("/tmp")) is False
    assert _safe_work_root(Path("/srv/baseline/work")) is True


def test_clear_removes_exact_runtime_roots_and_preserves_input_harness(tmp_path):
    root = tmp_path / "isolated" / "work"
    _prepare(root)

    clear_workspace(root)

    assert (root / "input" / "task.md").read_text() == "frozen task\n"
    assert (root / "harness" / "keep").read_text() == "yes"
    for child in ("agent", "state", "submission", "logs"):
        assert list((root / child).iterdir()) == []


def test_clear_refuses_changed_frozen_input_before_deleting_drill(tmp_path):
    root = tmp_path / "isolated" / "work"
    _prepare(root)
    (root / "input" / "task.md").write_text("changed")

    with pytest.raises(ValueError, match="input manifest mismatch"):
        clear_workspace(root)

    assert (root / "state" / "drill-only").is_file()


def test_clear_removes_external_drill_candidates_and_recreates_roots(tmp_path, monkeypatch):
    retained = tmp_path / "var" / "lib" / "tidmad-baseline"
    transient = retained / ".candidate-001.snapshot.random"
    transient.mkdir(parents=True)
    (transient / "weights.pth").write_bytes(b"partial")
    unrelated_hidden = retained / ".operator-note"
    unrelated_hidden.mkdir()
    (unrelated_hidden / "keep").write_text("yes")
    (retained / "candidates" / "drill").mkdir(parents=True)
    (retained / "candidates" / "drill" / "weights.pth").write_bytes(b"drill")
    (retained / "evaluations" / "0-3").mkdir(parents=True)
    (retained / "evaluations" / "0-3" / "drill.json").write_text("{}")
    (retained / "health-configs" / "scope-0-1-2-3").mkdir(parents=True)
    (retained / "health-configs" / "scope-0-1-2-3" / "effective.yaml").write_text("drill")
    (retained / "backup-receipts").mkdir()
    (retained / "inference-sessions" / "drill").mkdir(parents=True)
    (retained / "final_score.json").write_text("{}")
    (retained / "final_attempt.json").write_text("{}")
    (retained / "final_failure.json").write_text("{}")
    monkeypatch.setattr("shutil.chown", lambda *_args, **_kwargs: None)

    clear_retained_state(
        retained,
        evaluator_user="evaluator",
        results_group="results",
        backup_user="backup",
        inference_group="inference",
        expected_root=retained,
    )

    assert list((retained / "candidates").iterdir()) == []
    assert list((retained / "evaluations").iterdir()) == []
    assert list((retained / "health-configs").iterdir()) == []
    assert list((retained / "backup-receipts").iterdir()) == []
    assert list((retained / "inference-sessions").iterdir()) == []
    assert not transient.exists()
    assert (unrelated_hidden / "keep").read_text() == "yes"
    assert not (retained / "final_score.json").exists()
    assert not (retained / "final_attempt.json").exists()
    assert not (retained / "final_failure.json").exists()
