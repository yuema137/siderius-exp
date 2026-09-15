from __future__ import annotations

import hashlib

import pytest

from deployments.tidmad_coding_agent_baseline.tools.clear_workspace import (
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


def test_clear_removes_external_drill_candidates_and_recreates_roots(
    tmp_path, monkeypatch
):
    retained = tmp_path / "var" / "lib" / "tidmad-baseline"
    (retained / "candidates" / "drill").mkdir(parents=True)
    (retained / "candidates" / "drill" / "weights.pth").write_bytes(b"drill")
    (retained / "backup-receipts").mkdir()
    (retained / "final_score.json").write_text("{}")
    monkeypatch.setattr("shutil.chown", lambda *_args, **_kwargs: None)

    clear_retained_state(
        retained,
        evaluator_user="evaluator",
        results_group="results",
        backup_user="backup",
        expected_root=retained,
    )

    assert list((retained / "candidates").iterdir()) == []
    assert list((retained / "backup-receipts").iterdir()) == []
    assert not (retained / "final_score.json").exists()
