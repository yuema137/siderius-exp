"""The launcher policy is derived from the deployment, not typed.

* ``test_a_drafted_policy_verifies_and_pins_what_the_interpreter_reports`` —
  the entrypoint is the training script the framework on THAT interpreter
  will emit, the constructor digest equals what the framework computes
  in-process (an oracle the drafter's subprocess cannot share), and the
  result passes the same verifier an installed policy must pass.
* ``test_only_the_training_namespace_may_write`` — the caller's workspace
  is bound writable for training and nowhere else; the probe and the
  numeric worker run caller-influenced code with no host write path.
* ``test_a_deployment_missing_its_truth_manifest_is_refused`` — the drafter
  names what is missing instead of writing a policy with a hole in it.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
from ml_models import models_sandbox

from experiments.phyts_tess.main_orchestrator.draft_launcher_policy import (
    draft_launcher_policy,
)
from experiments.phyts_tess.main_orchestrator.verify_launcher_policy import (
    verify_launcher_policy,
)

EXP_ROOT = Path(__file__).resolve().parents[2]


def _deployment(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "deployment"
    (root / "framework").mkdir(parents=True)
    # This test process's venv has the framework installed, so the drafter's
    # facts subprocess runs against a real `core.sandbox_executor`. The whole
    # venv is linked: a bare `python` symlink without its `pyvenv.cfg` would
    # start an interpreter with no site-packages.
    (root / "framework" / ".venv").symlink_to(Path(sys.executable).parents[1])
    runtime = root / "runtime" / "experiments" / "shared"
    runtime.mkdir(parents=True)
    shutil.copyfile(
        EXP_ROOT / "experiments/shared/native_training_entry.py",
        runtime / "native_training_entry.py",
    )
    caller = root / "bundle" / "caller"
    (caller / "tasks/phyts_tess/declared").mkdir(parents=True)
    (caller / "composition.yaml").write_text("task_data_path: {}\n", encoding="utf-8")
    shutil.copyfile(
        EXP_ROOT / "tasks/phyts_tess/declared/dataset_profile.json",
        caller / "tasks/phyts_tess/declared/dataset_profile.json",
    )
    truth = (
        root / "bundle/evaluator/tasks/phyts_tess/data/manifests/rotation_identity.csv"
    )
    truth.parent.mkdir(parents=True)
    truth.write_text("split,gaia_id,tic,sector,frot,frot_err\n", encoding="utf-8")
    (root / "views/agent/manifests").mkdir(parents=True)
    data = tmp_path / "rundata"
    data.mkdir()
    (data / "tess_rotation_val.npz").write_bytes(b"")
    work = tmp_path / "caller-work"
    work.mkdir()
    return root, data, work


def _draft(tmp_path: Path) -> dict:
    root, data, work = _deployment(tmp_path)
    return draft_launcher_policy(
        root=root,
        data_dir=data,
        caller_uid=1001,
        caller_gid=1001,
        coordinator_uid=1002,
        caller_work=work,
        system_mounts=(),
        device_nodes=(),
    )


def test_a_drafted_policy_verifies_and_pins_what_the_interpreter_reports(tmp_path):
    policy = _draft(tmp_path)
    out = tmp_path / "policy.json"
    out.write_text(json.dumps(policy), encoding="utf-8")

    receipt = verify_launcher_policy(out)

    runtime = policy["settings"]["runtime"]
    assert receipt["entrypoint"].endswith("execute_tools/train_engine_sandbox.py")
    assert Path(runtime["entrypoint"]).is_file()
    assert (
        runtime["constructor_sha256"]
        == models_sandbox.registered_model_construction_implementation_sha256()
    )
    assert receipt["cwd"] == str(tmp_path / "deployment" / "runtime")
    assert (
        receipt["truth_manifest_sha256"] == policy["settings"]["truth_manifest_sha256"]
    )


def test_only_the_training_namespace_may_write(tmp_path):
    runtime = _draft(tmp_path)["settings"]["runtime"]

    def writable(namespace: str) -> list[str]:
        return [
            m["source"] for m in runtime[namespace]["mounts"] if m["mode"] == "write"
        ]

    assert writable("training_namespace") == [str(tmp_path / "caller-work")]
    assert writable("probe_namespace") == []
    assert writable("worker_namespace") == []


def test_a_deployment_missing_its_truth_manifest_is_refused(tmp_path):
    root, data, work = _deployment(tmp_path)
    truth = (
        root / "bundle/evaluator/tasks/phyts_tess/data/manifests/rotation_identity.csv"
    )
    truth.rename(truth.with_suffix(".moved-aside"))

    with pytest.raises(FileNotFoundError, match="truth manifest is missing"):
        draft_launcher_policy(
            root=root,
            data_dir=data,
            caller_uid=1001,
            caller_gid=1001,
            coordinator_uid=1002,
            caller_work=work,
            system_mounts=(),
            device_nodes=(),
        )


def test_every_symlink_hop_of_the_interpreter_is_mounted(tmp_path):
    """The deployment's venv python links through a LINKED directory.

    bwrap resolves that chain inside the namespace. Mounting only the
    resolved interpreter tree left the linked directory absent, and the
    first real probe died with `execvp … No such file or directory`.
    """
    from experiments.phyts_tess.main_orchestrator.draft_launcher_policy import (
        interpreter_mounts,
    )

    real = tmp_path / "pyroot" / "cpython-3.12.13-linux"
    (real / "bin").mkdir(parents=True)
    (real / "bin" / "python3.12").write_text("", encoding="utf-8")
    (tmp_path / "pyroot" / "cpython-3.12-linux").symlink_to(real)
    venv_bin = tmp_path / "framework" / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python").symlink_to(
        tmp_path / "pyroot" / "cpython-3.12-linux" / "bin" / "python3.12"
    )

    mounts = interpreter_mounts(venv_bin / "python", [tmp_path / "framework"])

    assert mounts == [tmp_path / "pyroot"], (
        "the nearest ancestor without a symlink component covers the linked "
        "directory and the one it points at"
    )


def test_the_caller_work_dir_is_a_readable_root_and_mounted_everywhere(tmp_path):
    """Capture and plugin discovery resolve against readable_roots; the tuner's
    inputs live in the caller's work directory, so it must be one — and the
    probe that discovers model source must see it too."""
    policy = _draft(tmp_path)
    runtime = policy["settings"]["runtime"]
    work = str(tmp_path / "caller-work")

    assert work in runtime["readable_roots"]
    for namespace in ("probe_namespace", "training_namespace", "worker_namespace"):
        sources = [m["source"] for m in runtime[namespace]["mounts"]]
        assert sources.count(work) == 1, namespace
