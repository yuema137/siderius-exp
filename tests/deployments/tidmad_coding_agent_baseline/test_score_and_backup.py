from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pytest
from deployments.tidmad_coding_agent_baseline.tools import (
    backup_completed,
    final_inference,
    score,
)
from deployments.tidmad_coding_agent_baseline.tools.evaluator_policy import (
    EvaluatorPolicy,
)
from deployments.tidmad_coding_agent_baseline.tools.health import (
    CandidateHealthEvaluation,
)


def _candidate_args(tmp_path):
    source = tmp_path / "agent" / "source"
    source.mkdir(parents=True)
    (source / "model.py").write_text("MODEL = 'test'\n")
    (source / "architecture.json").write_text(json.dumps({"kind": "test"}))
    (source / "train_config.json").write_text(json.dumps({"epochs": 1}))
    (source / "weights.pth").write_bytes(b"weights")
    (source / "predict.py").write_text("raise SystemExit('test fixture only')\n")
    return argparse.Namespace(
        workers=1,
        candidate_source=source,
        band="0-3",
        candidate_id="candidate-1",
    )


def _policy(tmp_path):
    scope_root = tmp_path / "scopes"
    scope_root.mkdir(parents=True)
    (scope_root / "band-0-3-development.json").write_text('{"3":[0]}')
    return EvaluatorPolicy(
        input_root=tmp_path / "input",
        scope_root=scope_root,
        development_truth_dir=tmp_path / "development-truth",
        development_input_dir=tmp_path / "development-input",
        final_input_dir=tmp_path / "final-input",
        final_truth_dir=tmp_path / "final-truth",
        agent_root=tmp_path / "agent",
        archive_root=tmp_path / "state" / "candidates",
        evaluation_root=tmp_path / "state" / "evaluations",
        health_config_root=tmp_path / "state" / "health-configs",
        final_output_dir=tmp_path / "state" / "final-denoised",
        final_score=tmp_path / "state" / "final_score.json",
    )


def _health(*, eligible=True):
    return CandidateHealthEvaluation(
        status="valid" if eligible else "invalid",
        eligible=eligible,
        effective_config_sha256="a" * 64,
        gate_results=[
            {
                "gate_name": "amplitude_collapse_blocking",
                "execution_status": "passed" if eligible else "failed",
                "check_passed": eligible,
            }
        ],
    )


def _deliverables(tmp_path):
    paths = [tmp_path / "denoised-3.h5"]
    for path in paths:
        path.write_bytes(b"temporary")
    return paths


def test_candidate_scoring_deletes_deliverables_only_after_durable_archive(tmp_path, monkeypatch):
    args = _candidate_args(tmp_path)
    deliverables = _deliverables(tmp_path)
    events = []
    monkeypatch.setenv("BASELINE_RUN_ID", "codex-100")
    monkeypatch.setenv("BASELINE_INVOCATION_ID", "codex-100-invocation-0001")
    monkeypatch.setattr(
        score,
        "run_candidate_inference",
        lambda **kwargs: kwargs["output_root"].mkdir() or kwargs["output_root"],
    )

    monkeypatch.setattr(
        score,
        "compute_score",
        lambda **_kwargs: (
            {
                "scoreable": True,
                "valid": False,
                "scalar": 1.0,
                "file_vector": [None, None, None, 1.0] + [None] * 16,
            },
            deliverables,
        ),
    )
    monkeypatch.setattr(score, "evaluate_candidate_health", lambda **_kwargs: _health())

    def archive(**kwargs):
        assert all(path.exists() for path in deliverables)
        assert kwargs["score_path"].exists()
        receipt = json.loads(kwargs["score_path"].read_text())
        assert receipt["score_utc"].endswith("Z")
        assert receipt["run_id"] == "codex-100"
        assert receipt["invocation_id"] == "codex-100-invocation-0001"
        events.append("archive")
        return tmp_path / "published"

    monkeypatch.setattr(score, "archive_candidate", archive)
    assert score.score_candidate(args, _policy(tmp_path)) == tmp_path / "published"
    assert events == ["archive"]
    assert not any(path.exists() for path in deliverables)


def test_candidate_scoring_keeps_deliverables_when_archive_fails(tmp_path, monkeypatch):
    args = _candidate_args(tmp_path)
    deliverables = _deliverables(tmp_path)
    monkeypatch.setattr(
        score,
        "run_candidate_inference",
        lambda **kwargs: kwargs["output_root"].mkdir() or kwargs["output_root"],
    )
    monkeypatch.setattr(
        score,
        "compute_score",
        lambda **_kwargs: (
            {
                "scoreable": True,
                "valid": False,
                "scalar": 1.0,
                "file_vector": [None, None, None, 1.0] + [None] * 16,
            },
            deliverables,
        ),
    )
    monkeypatch.setattr(score, "evaluate_candidate_health", lambda **_kwargs: _health())
    monkeypatch.setattr(
        score,
        "archive_candidate",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("archive failed")),
    )
    with pytest.raises(RuntimeError, match="archive failed"):
        score.score_candidate(args, _policy(tmp_path))
    assert all(path.exists() for path in deliverables)


def test_health_failure_returns_raw_feedback_but_never_archives_or_selects(tmp_path, monkeypatch):
    args = _candidate_args(tmp_path)
    deliverables = _deliverables(tmp_path)
    monkeypatch.setattr(
        score,
        "run_candidate_inference",
        lambda **kwargs: kwargs["output_root"].mkdir() or kwargs["output_root"],
    )
    monkeypatch.setattr(
        score,
        "compute_score",
        lambda **_kwargs: (
            {
                "scoreable": True,
                "valid": False,
                "scalar": 22.0,
                "file_vector": [None, None, None, 22.0] + [None] * 16,
            },
            deliverables,
        ),
    )
    monkeypatch.setattr(
        score, "evaluate_candidate_health", lambda **_kwargs: _health(eligible=False)
    )
    monkeypatch.setattr(
        score,
        "archive_candidate",
        lambda **_kwargs: pytest.fail("Health-invalid candidate reached archive"),
    )

    receipt = score.score_candidate(args, _policy(tmp_path))
    payload = json.loads(receipt.read_text())
    assert payload["scalar"] == 22.0
    assert payload["scoreable"] is True
    assert payload["health_passed"] is False
    assert payload["health_status"] == "invalid"
    assert payload["eligible_for_selection"] is False
    assert payload["valid"] is False
    assert all(path.exists() for path in deliverables)


def test_final_scoring_refuses_health_failure_before_writing_or_deleting(tmp_path, monkeypatch):
    """A raw-complete final submission must not bypass task Health."""

    deliverables = [tmp_path / f"denoised-{index}.h5" for index in range(20)]
    for path in deliverables:
        path.write_bytes(b"temporary")
    policy = _policy(tmp_path)
    policy.final_output_dir.mkdir(parents=True)
    (policy.scope_root / "all-final.json").write_text(
        json.dumps({str(index): [0] for index in range(20)})
    )
    args = argparse.Namespace(
        denoised_dir=policy.final_output_dir,
        workers=1,
        winner=[f"{band}=candidate-{band}" for band in ("0-3", "4-9", "10-14", "15-19")],
    )
    monkeypatch.setattr(
        score,
        "compute_score",
        lambda **_kwargs: (
            {
                "scoreable": True,
                "valid": False,
                "scalar": 22.0,
                "file_vector": [22.0] * 20,
            },
            deliverables,
        ),
    )
    monkeypatch.setattr(
        score, "evaluate_candidate_health", lambda **_kwargs: _health(eligible=False)
    )

    with pytest.raises(ValueError, match="refused by task Health"):
        score.score_final(args, policy)

    assert not policy.final_score.exists()
    assert all(path.exists() for path in deliverables)


def test_task_health_materialization_is_band_scoped_and_regression_appropriate(
    tmp_path,
):
    from execute_tools.health_checks.config import (
        default_health_policy_path,
        load_health_gates_config,
        materialize_effective_config,
    )

    repo = Path(__file__).resolve().parents[3]
    binding = repo / "tasks/tidmad/framework_configs/health_regression.yaml"
    path, _sha = materialize_effective_config(
        source_path=default_health_policy_path(),
        files=[0, 1, 2, 3],
        workspace=str(tmp_path),
        resolved_scope=[0, 1, 2, 3],
        task_health_binding=str(binding),
        dataset_partition_count=20,
    )
    config = load_health_gates_config(path)
    roles = {gate.id: gate.gate_role for gate in config.health_gates}
    assert roles["amplitude_collapse_blocking"] == "blocking"
    assert roles["output_diversity_blocking"] == "observational"
    assert roles["output_std_blocking"] == "observational"
    for gate in config.health_gates:
        for check in gate.checks:
            if "peek_file_indices" in check.config:
                assert check.config["peek_file_indices"] == [0, 1, 2, 3]


def test_privileged_scorer_refuses_agent_selected_scientific_roots(tmp_path):
    args = _candidate_args(tmp_path)
    args.candidate_source = tmp_path / "outside" / "candidate"
    args.candidate_source.mkdir(parents=True)

    with pytest.raises(ValueError, match="candidate source must remain below"):
        score.score_candidate(args, _policy(tmp_path))


def test_inference_command_hides_file_identity_and_blocks_network(tmp_path):
    runtime = final_inference.FinalInferenceRuntime(
        python=tmp_path / "immutable-python",
        systemd_run=tmp_path / "systemd-run",
        session_root=tmp_path / "sessions",
    )
    command = final_inference._command(
        runtime=runtime,
        candidate=tmp_path / "candidate",
        input_path=tmp_path / "session" / "input.h5",
        output_path=tmp_path / "session" / "output.h5",
        session_root=tmp_path / "session",
    )

    assert str(runtime.python) in command
    assert "--property=RestrictAddressFamilies=AF_UNIX" in command
    assert "--property=KillMode=control-group" in command
    assert not any("file-index" in argument for argument in command)
    assert not any("abra_validation" in argument for argument in command)


def test_public_score_cli_has_no_final_mode(monkeypatch):
    monkeypatch.setattr("sys.argv", ["tidmad-score", "final"])
    with pytest.raises(SystemExit) as refusal:
        score.main()
    assert refusal.value.code == 2


def test_privileged_snapshot_never_follows_agent_symlinks(tmp_path, monkeypatch):
    args = _candidate_args(tmp_path)
    hidden = tmp_path / "private-validation"
    hidden.mkdir()
    (hidden / "truth.h5").write_bytes(b"hidden truth")
    (args.candidate_source / "borrowed-truth").symlink_to(hidden, target_is_directory=True)
    monkeypatch.setattr(
        score,
        "compute_score",
        lambda **_kwargs: pytest.fail("invalid snapshot reached the scorer"),
    )

    with pytest.raises(ValueError, match="contains a symlink"):
        score.score_candidate(args, _policy(tmp_path))


def test_backup_uses_conditional_create_and_records_completed_candidate(tmp_path, monkeypatch):
    candidate = tmp_path / "candidates" / "0-3" / "candidate-1"
    candidate.mkdir(parents=True)
    (candidate / "candidate_manifest.json").write_text('{"candidate_id":"candidate-1"}')
    (candidate / "COMPLETE.json").write_text('{"complete":true}')
    calls = []

    def fake_aws(*args, timeout_seconds):
        calls.append((args, timeout_seconds))
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(backup_completed, "_aws", fake_aws)
    outcomes = backup_completed.backup_completed(
        tmp_path / "candidates",
        bucket="condition-only",
        prefix="codex",
        receipts=tmp_path / "receipts",
        timeout_seconds=42,
    )

    assert outcomes == [(candidate, "created")]
    assert "--if-none-match" in calls[0][0]
    assert calls[0][0][calls[0][0].index("--if-none-match") + 1] == "*"
    assert calls[0][1] == 42
    assert backup_completed.backup_completed(
        tmp_path / "candidates",
        bucket="condition-only",
        prefix="codex",
        receipts=tmp_path / "receipts",
        timeout_seconds=42,
    ) == [(candidate, "already-recorded")]
    assert len(calls) == 1


def test_backup_uses_configured_s3_compatible_endpoint(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setenv("BACKUP_ENDPOINT", "https://storage.example.test")
    monkeypatch.setattr(
        backup_completed.subprocess,
        "run",
        lambda command, **kwargs: (
            calls.append((command, kwargs)) or subprocess.CompletedProcess(command, 0, "{}", "")
        ),
    )

    backup_completed._aws("s3api", "head-object", timeout_seconds=10)

    assert calls[0][0][:3] == [
        "aws",
        "--endpoint-url",
        "https://storage.example.test",
    ]


def test_backup_refuses_preexisting_object_with_different_candidate_identity(tmp_path, monkeypatch):
    candidate = tmp_path / "candidates" / "0-3" / "candidate-1"
    candidate.mkdir(parents=True)
    (candidate / "candidate_manifest.json").write_text('{"candidate_id":"candidate-1"}')
    (candidate / "COMPLETE.json").write_text('{"complete":true}')

    def fake_aws(*args, timeout_seconds):
        if args[1] == "put-object":
            return subprocess.CompletedProcess(args, 1, "", "PreconditionFailed 412")
        return subprocess.CompletedProcess(
            args,
            0,
            '{"Metadata":{"candidate-manifest-sha256":"different"}}',
            "",
        )

    monkeypatch.setattr(backup_completed, "_aws", fake_aws)
    with pytest.raises(RuntimeError, match="different candidate identity"):
        backup_completed.backup_completed(
            tmp_path / "candidates",
            bucket="condition-only",
            prefix="codex",
            receipts=tmp_path / "receipts",
            timeout_seconds=42,
        )


def test_backup_publishes_completed_final_submission(tmp_path, monkeypatch):
    submission = tmp_path / "submission"
    submission.mkdir()
    (submission / "manifest.json").write_text('{"complete":true}')
    (submission / "COMPLETE.json").write_text('{"complete":true}')
    calls = []

    def fake_aws(*args, timeout_seconds):
        calls.append((args, timeout_seconds))
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(backup_completed, "_aws", fake_aws)
    outcomes = backup_completed.backup_completed(
        tmp_path / "candidates",
        bucket="condition-only",
        prefix="codex",
        receipts=tmp_path / "receipts",
        timeout_seconds=42,
        submission_root=submission,
    )

    assert outcomes == [(submission, "created")]
    assert "/submission/" in calls[0][0][calls[0][0].index("--key") + 1]
