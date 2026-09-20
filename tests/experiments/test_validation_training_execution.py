"""Native exits must not leave the epoch service waiting until a run deadline."""

import os
import sys
import time
from pathlib import Path

import pytest
from execute_tools.validation_execution import ValidationDeployment
from ml_models.models_format_sandbox import LossConfig

from experiments.shared.validation_epoch_service import AdmittedValidationWorkload
from experiments.shared.validation_training_execution import (
    run_admitted_native_training,
)


def _run(tmp_path, source, *, timeout, execute=None):
    entrypoint = tmp_path / "native_fixture.py"
    entrypoint.write_text(source)
    workload = AdmittedValidationWorkload(
        model_type="fixture",
        configuration={},
        model_io=None,
        loss=LossConfig(loss_type="smooth_l1"),
        scope_payload="operator-scope",
        device="cpu",
        batch_size=1,
        expected_rows=1,
        max_epochs=2,
        optimizer_steps_per_epoch=1,
    )

    def no_validation(*args):
        pytest.fail("an exited or idle child must not trigger private validation")

    return run_admitted_native_training(
        [sys.executable, str(entrypoint), "--validation_executor_json={}"],
        python=Path(sys.executable),
        entrypoint=entrypoint,
        deployment=ValidationDeployment(factory="unused.client:create", settings={}),
        environment={"PATH": os.defpath},
        confinement_prefix=(),
        cwd=tmp_path,
        workload=workload,
        execute=execute or no_validation,
        deadline=time.monotonic() + timeout,
        max_metadata_bytes=100000,
        max_snapshot_bytes=10000,
        entry_module=None,
    )


@pytest.mark.parametrize("returncode", [0, 7])
def test_native_rejection_or_failure_exits_without_waiting_for_epochs(
    tmp_path, returncode
):
    result = _run(tmp_path, f"raise SystemExit({returncode})\n", timeout=10)
    assert result.returncode == returncode
    assert result.validation_epochs == 0
    assert result.elapsed_seconds < 3


def test_idle_native_job_deadline_reaps_the_process(tmp_path):
    with pytest.raises(TimeoutError, match="deadline exhausted"):
        _run(
            tmp_path,
            "import os,time\nfrom pathlib import Path\n"
            "Path('child.pid').write_text(str(os.getpid()))\ntime.sleep(30)\n",
            timeout=0.5,
        )
    pid = int((tmp_path / "child.pid").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


@pytest.mark.parametrize("exit_code", [0, 7])
def test_cancelled_epoch_preserves_native_exit_and_never_counts_completion(
    tmp_path, exit_code
):
    root = str(Path(__file__).resolve().parents[2])
    source = f"""
import sys
sys.path.insert(0, {root!r})
import json,socket,time,torch
from experiments.shared.validation_epoch_protocol import ValidationEpochMetadata,ValidationCancelled
from experiments.shared.validation_descriptor_transport import send_snapshots
from experiments.shared.validation_frames import read_frame,write_frame
from experiments.shared.validation_rng import capture_validation_rng
from experiments.shared.validation_snapshot import sealed_tensor_state
from execute_tools.validation_execution import CompletedTrainingEpoch
from ml_models.models_format_sandbox import LossConfig
cfg=json.loads(sys.argv[2]); channel=socket.socket(fileno=cfg['settings']['channel_fd'])
deadline=time.monotonic()+10
request=ValidationEpochMetadata(sequence=0,model_type='fixture',configuration={{}},model_io=None,
 loss=LossConfig(loss_type='smooth_l1'),scope_payload='operator-scope',device='cpu',batch_size=1,
 expected_rows=1,model_training=False,objective_training=False,rng=capture_validation_rng(),
 completed_training=CompletedTrainingEpoch(completed_epochs=1,optimizer_steps=1))
with sealed_tensor_state({{'weight':torch.ones(1)}},max_tensor_bytes=10000) as model, sealed_tensor_state({{}},max_tensor_bytes=10000) as loss:
 send_snapshots(channel,request.model_dump_json().encode(),[model.fd,loss.fd],deadline=deadline,max_metadata_bytes=100000)
 reply=json.loads(read_frame(channel.fileno(),max_bytes=100000,deadline=deadline))
 assert reply['kind']=='progress'
 write_frame(channel.fileno(),ValidationCancelled(sequence=0).model_dump_json().encode(),max_bytes=100000,deadline=deadline)
channel.close()
raise SystemExit({exit_code})
"""

    def execute(request, snapshots, progress):
        progress.feed(15.0, elapsed_ms=15.0)
        pytest.fail("cancelled validation must not return an aggregate")

    result = _run(tmp_path, source, timeout=20, execute=execute)
    assert result.returncode == exit_code
    assert result.validation_epochs == 0
    assert result.elapsed_seconds < 10
