"""Capture effective native argv, keeping mutable research paths out of execution."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from execute_tools.training_cli import build_training_parser

from experiments.shared.native_training_inputs import capture_native_training_inputs


def _setup(tmp_path):
    research = tmp_path / "research"
    research.mkdir()
    operator = tmp_path / "operator"
    operator.mkdir(mode=0o700)
    for name in ("model", "train", "loss"):
        (research / f"{name}.json").write_text(json.dumps({"kind": name}))
    command = [
        "python",
        "native.py",
        "--model_cfg",
        "absent.json",
        "--model_c=model.json",
        "--train_cfg",
        "train.json",
        "--loss_cfg=loss.json",
        "--exp_id",
        "preserved",
        "--task_manifest",
        "composition.yaml",
    ]
    settings = {
        "python": Path("python"),
        "entrypoint": Path("native.py"),
        "source_cwd": research,
        "allowed_roots": (research,),
        "parent": operator,
        "owner_uid": os.geteuid(),
        "max_file_bytes": 10000,
    }
    return research, operator, command, settings


def test_parallel_captures_preserve_native_last_value_and_isolate_files(tmp_path):
    research, _, command, settings = _setup(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        captures = list(
            pool.map(
                lambda _: capture_native_training_inputs(command, **settings), range(2)
            )
        )
    assert captures[0].root != captures[1].root
    (research / "model.json").write_text('{"kind":"changed"}')
    for capture in captures:
        args = build_training_parser().parse_args(capture.command[2:])
        assert json.loads(Path(args.model_cfg).read_text()) == {"kind": "model"}
        assert args.exp_id == "preserved" and args.task_manifest == "composition.yaml"
        assert len(capture.files) == 3
        assert not Path(args.model_cfg).stat().st_mode & 0o222


def test_escape_symlink_refuses_before_creating_snapshot(tmp_path):
    research, operator, command, settings = _setup(tmp_path)
    private = tmp_path / "private.json"
    private.write_text('{"private":"must not be copied"}')
    (research / "model.json").unlink()
    (research / "model.json").symlink_to(private)
    with pytest.raises(PermissionError, match="outside operator-selected roots"):
        capture_native_training_inputs(command, **settings)
    assert list(operator.iterdir()) == []


def test_invalid_later_input_leaves_no_partial_snapshot(tmp_path):
    research, operator, command, settings = _setup(tmp_path)
    (research / "loss.json").write_text("not JSON")
    with pytest.raises(json.JSONDecodeError):
        capture_native_training_inputs(command, **settings)
    assert list(operator.iterdir()) == []


def test_task_scope_transport_keeps_non_json_payload_and_native_digest(tmp_path):
    from execute_tools.scope_artifact import read_scope_artifact, scope_digest

    research, _, command, settings = _setup(tmp_path)
    payload = "opaque-task-scope-v1\npartition alpha: window 3..8\n"
    (research / "scope.txt").write_text(payload)
    digest = scope_digest(payload)
    command.extend(
        [
            "--task_scope_ref",
            "scope.txt",
            "--task_scope_digest",
            digest,
            "--task_eval_scope_ref",
            "scope.txt",
            "--task_eval_scope_digest",
            digest,
        ]
    )
    capture = capture_native_training_inputs(command, **settings)
    args = build_training_parser().parse_args(capture.command[2:])
    assert read_scope_artifact(args.task_scope_ref, args.task_scope_digest) == payload
    assert (
        read_scope_artifact(args.task_eval_scope_ref, args.task_eval_scope_digest)
        == payload
    )


@pytest.mark.parametrize("observation", [False, True])
def test_captured_metadata_preserves_native_budget_activation(tmp_path, observation):
    from experiments.shared.epoch_model_worker import EpochModelSource
    from experiments.shared.native_training_metadata import (
        captured_configuration_request,
    )

    research, _, command, settings = _setup(tmp_path)
    for name, value in (
        ("model", {"model_type": "fixture"}),
        ("train", {"epochs": 7}),
        ("loss", {"loss_type": "smooth_l1"}),
        (
            "policy",
            {
                "training_budget": {
                    "max_epochs": 100,
                    "budget_seconds": 600,
                    "reserve_fraction": 0.1,
                    "started_monotonic_seconds": 1,
                }
            },
        ),
    ):
        (research / f"{name}.json").write_text(json.dumps(value))
    command.extend(["--runtime_policy_json", "policy.json"])
    if observation:
        command.extend(["--runtime_observation_out", "runtime.json"])
    captured = capture_native_training_inputs(command, **settings)
    source = EpochModelSource(
        model_type="fixture", constructor_sha256="a" * 64, source_sha256="b" * 64
    )
    request, limit = captured_configuration_request(captured, source=source)
    assert request.training.epochs == 7
    assert limit == (100 if observation else 7)
    # A protected capture was accidentally made writable/changed: do not silently
    # use a different configuration from the one admitted by the launcher.
    train = next(
        item.captured for item in captured.files if item.argument == "train_cfg"
    )
    train.chmod(0o644)
    train.write_text('{"epochs": 3}')
    with pytest.raises(ValueError, match="changed after capture"):
        captured_configuration_request(captured, source=source)
