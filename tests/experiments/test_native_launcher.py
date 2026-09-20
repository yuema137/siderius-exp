"""Caller and policy boundary, before any candidate import or execution."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.shared.native_launcher import (
    NativeLauncherPolicy,
    authorize_native_caller,
    read_launcher_policy,
)


def policy(tmp_path):
    return NativeLauncherPolicy(
        caller_uid=23456,
        caller_gid=23456,
        coordinator_uid=os.geteuid(),
        cwd=tmp_path,
        handler="experiments.shared.native_launcher:test_handler",
        settings={},
        environment={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
        deadline_epoch=100,
    )


@pytest.mark.parametrize(
    "uid,identity", [(23456, "23456"), (98765, "23456"), (None, "1"), (None, None)]
)
def test_wrong_account_cannot_reach_admission(tmp_path, uid, identity):
    selected = policy(tmp_path)
    environment = {"SUDO_UID": identity, "SUDO_GID": "23456"} if identity else {}
    with pytest.raises(PermissionError):
        authorize_native_caller(
            selected,
            effective_uid=os.geteuid() if uid is None else uid,
            environment=environment,
            source_cwd=tmp_path,
            now_epoch=10,
            now_monotonic=20,
        )


def test_authorized_call_preserves_original_deadline(tmp_path):
    selected = policy(tmp_path)
    arguments = {
        "effective_uid": os.geteuid(),
        "environment": {"SUDO_UID": "23456", "SUDO_GID": "23456"},
        "source_cwd": tmp_path,
    }
    result = authorize_native_caller(
        selected, **arguments, now_epoch=30, now_monotonic=80
    )
    assert result.deadline == 150
    with pytest.raises(TimeoutError):
        authorize_native_caller(selected, **arguments, now_epoch=100, now_monotonic=150)


def test_policy_refuses_symlink_and_other_user_writes(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text(policy(tmp_path).model_dump_json())
    path.chmod(0o600)
    assert read_launcher_policy(path, owner_uid=os.geteuid()) == policy(tmp_path)
    alias = tmp_path / "alias.json"
    alias.symlink_to(path)
    with pytest.raises(OSError):
        read_launcher_policy(alias, owner_uid=os.geteuid())
    path.chmod(0o666)
    with pytest.raises(PermissionError):
        read_launcher_policy(path, owner_uid=os.geteuid())


def test_disposable_dispatcher_uses_policy_environment_and_handler(tmp_path):
    import time

    selected = policy(tmp_path).model_copy(update={"deadline_epoch": time.time() + 15})
    path = tmp_path / "policy.json"
    path.write_text(selected.model_dump_json())
    path.chmod(0o600)
    # Exercise real dispatch in a child using our own test coordinator UID.
    # This proves routing/sanitization, not an actual installed sudo transition.
    code = """import os, sys
from pathlib import Path
import experiments.shared.native_launcher as launcher
def handler(context, command):
    assert command == ("python", "native.py", "--model_cfg", "research.json")
    assert Path.cwd() == context.policy.cwd
    assert dict(os.environ) == context.policy.environment
    assert "UNTRUSTED_MARKER" not in os.environ
    assert context.source_environment == {"SIDERIUS_PLUGIN_DIRS": "/research/plugins"}
    assert "SIDERIUS_PLUGIN_DIRS" not in os.environ
    return 7
launcher.test_handler = handler
sys.exit(launcher.dispatch_native_training(Path(sys.argv[1]), sys.argv[2:]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(path),
            "python",
            "native.py",
            "--model_cfg",
            "research.json",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={
            "PATH": os.defpath,
            "SUDO_UID": "23456",
            "SUDO_GID": "23456",
            "UNTRUSTED_MARKER": "must be cleared",
            "SIDERIUS_PLUGIN_DIRS": "/research/plugins",
        },
        check=False,
        timeout=10,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 7, result.stderr


def test_isolated_bootstrap_ignores_research_pythonpath(tmp_path):
    marker = tmp_path / "imported"
    package = tmp_path / "experiments"
    package.mkdir()
    (package / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
    )
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(root / "deployments/shared/native_training_entry.py"),
            str(tmp_path / "missing-policy.json"),
            "python",
            "native.py",
        ],
        cwd=tmp_path,
        env={"PATH": os.defpath, "PYTHONPATH": str(tmp_path)},
        check=False,
        timeout=10,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "FileNotFoundError" in result.stderr
    assert not marker.exists()
