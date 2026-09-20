"""Native builtin loss restoration must preserve config and optional buffers."""

import hashlib
import inspect
import os
import sys
import time
from pathlib import Path

import pytest
import torch
from ml_models.loss_models_sandbox import get_criterion
from ml_models.models_format_sandbox import LossConfig

from experiments.shared.builtin_objective_worker import BuiltinObjectiveWorkerConfig
from experiments.shared.validation_snapshot import sealed_tensor_state
from experiments.shared.validation_worker_process import launch_validation_worker


@pytest.mark.parametrize(
    "kind,weighted",
    [
        ("smooth_l1", False),
        ("focal", False),
        ("ce", False),
        ("ce", True),
        ("focal_cw", False),
        ("focal_cw", True),
    ],
)
def test_real_builtin_worker_matches_native_loss_and_state(tmp_path, kind, weighted):
    loss = LossConfig(loss_type=kind, reduction="sum", beta=0.7, gamma=1.5)
    weights = torch.tensor([0.2, 0.8]) if weighted else None
    native = get_criterion(loss, class_weights=weights).eval()
    prediction = torch.tensor([[[0.2, -0.5], [0.7, 0.3]]])
    target = torch.tensor([[1, 0]])
    if kind == "smooth_l1":
        target = torch.zeros_like(prediction)
    with sealed_tensor_state(native.state_dict(), max_tensor_bytes=1000) as snapshot:
        config = BuiltinObjectiveWorkerConfig(
            loss=loss,
            source_sha256=hashlib.sha256(
                Path(inspect.getfile(get_criterion)).read_bytes()
            ).hexdigest(),
            state_fd=snapshot.fd,
            max_snapshot_bytes=10000,
            training=False,
            device="cpu",
            deadline_epoch=time.time() + 15,
            max_frame_bytes=100000,
        )
        with launch_validation_worker(
            config,
            python=Path(sys.executable),
            cwd=Path(__file__).resolve().parents[2],
            config_path=tmp_path / "worker.json",
            stderr_path=tmp_path / "worker.stderr",
            environment={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
            confinement_prefix=(),
        ) as worker:
            for _ in range(2):
                torch.testing.assert_close(
                    worker.peer(prediction, target),
                    native(prediction, target),
                    rtol=0,
                    atol=0,
                )
            actual = worker.peer.state_dict()
            assert actual.keys() == native.state_dict().keys()
            for name, value in native.state_dict().items():
                torch.testing.assert_close(actual[name], value, rtol=0, atol=0)


def test_builtin_worker_reads_unmounted_owner_only_config(tmp_path, monkeypatch):
    import shutil

    from experiments.shared.validation_confinement import (
        NamespaceMount,
        ValidationNamespace,
    )

    if shutil.which("bwrap") is None:
        pytest.skip("bubblewrap not installed")
    root = Path(__file__).resolve().parents[2]
    paths = [
        Path(p)
        for p in ("/usr", "/lib", "/lib64", "/etc/ld.so.cache")
        if Path(p).exists()
    ]
    paths += [Path(sys.base_prefix).parent, root / ".venv", root / "experiments"]
    prefix = ValidationNamespace(
        bubblewrap=Path(shutil.which("bwrap")),
        cwd=root,
        mounts=tuple(NamespaceMount(source=p, target=p) for p in paths),
        # On a privileged qualification host this also exercises different IDs.
        uid=65534 if os.geteuid() == 0 else None,
        gid=65534 if os.geteuid() == 0 else None,
    ).prefix()
    original = launch_validation_worker

    def confined(config, **kwargs):
        kwargs["confinement_prefix"] = prefix
        return original(config, **kwargs)

    monkeypatch.setitem(globals(), "launch_validation_worker", confined)
    test_real_builtin_worker_matches_native_loss_and_state(tmp_path, "smooth_l1", False)
    assert (tmp_path / "worker.json").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "worker.stderr").stat().st_mode & 0o777 == 0o600
