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


def _run(tmp_path, source, *, timeout):
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
        execute=no_validation,
        deadline=time.monotonic() + timeout,
        max_metadata_bytes=10000,
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
