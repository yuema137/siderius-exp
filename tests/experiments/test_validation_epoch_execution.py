import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from agent.schemas.model_io_contract import ModelIOContract
from execute_tools.validation_execution import CompletedTrainingEpoch
from ml_models.models_format_sandbox import LossConfig
from torch.utils.data import TensorDataset

from experiments.shared.validation_epoch_execution import (
    ValidationProgressRelay,
    execute_admitted_epoch,
)
from experiments.shared.validation_epoch_protocol import (
    ValidationBatchProgress,
    ValidationContinue,
    ValidationEpochMetadata,
)
from experiments.shared.validation_frames import read_frame, write_frame
from experiments.shared.validation_module_peer import ModulePeer
from experiments.shared.validation_rng import capture_validation_rng

WORKER = """
import sys,time,torch
from experiments.shared.validation_module_worker import serve_module
role=sys.argv[1]
if role=='model':
    module=torch.nn.Linear(2,2,bias=False)
    module.weight.data.copy_(torch.eye(2)*3)
else:
    module=torch.nn.SmoothL1Loss()
raise SystemExit(serve_module(module,role=role,device=torch.device('cpu'),input_fd=0,output_fd=1,deadline=time.monotonic()+20,max_frame_bytes=100000))
"""


@pytest.mark.parametrize("bad_ack", [False, True])
def test_native_estimator_with_two_real_workers_and_acknowledged_progress(bad_ack):
    processes = []
    peers = []
    server, client = socket.socketpair()
    deadline = time.monotonic() + 15
    try:
        for role in ("model", "objective"):
            process = subprocess.Popen(
                [sys.executable, "-c", WORKER, role],
                cwd=Path(__file__).resolve().parents[2],
                env={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            processes.append(process)
            peers.append(
                ModulePeer(
                    input_fd=process.stdin.fileno(),
                    output_fd=process.stdout.fileno(),
                    device=torch.device("cpu"),
                    deadline=deadline,
                    max_frame_bytes=100000,
                )
            )
        io = ModelIOContract.model_validate(
            {
                name: {
                    "axes": [
                        {"role": "batch", "dimension": {"symbolic": "B"}},
                        {"role": "temporal", "dimension": {"fixed": 2}},
                    ],
                    "dtype": {"admissible": ["float32"]},
                }
                for name in ("input", "output")
            }
        )
        request = ValidationEpochMetadata(
            sequence=0,
            model_type="synthetic_linear",
            configuration={"model_type": "synthetic_linear"},
            completed_training=CompletedTrainingEpoch(
                completed_epochs=1, optimizer_steps=1
            ),
            model_io=io,
            loss=LossConfig(loss_type="smooth_l1"),
            scope_payload="synthetic",
            device="cpu",
            batch_size=3,
            expected_rows=7,
            model_training=True,
            objective_training=True,
            rng=capture_validation_rng(),
        )
        progress = ValidationProgressRelay(
            server,
            sequence=0,
            expected_rows=7,
            deadline=deadline,
            max_metadata_bytes=100000,
        )
        x = torch.arange(14).reshape(7, 2).float()
        y = x * 2
        events = []

        def acknowledge():
            for _ in range(1 if bad_ack else 3):
                event = ValidationBatchProgress.model_validate_json(
                    read_frame(client.fileno(), max_bytes=100000, deadline=deadline)
                )
                events.append(event.rows)
                write_frame(
                    client.fileno(),
                    ValidationContinue(sequence=1 if bad_ack else 0)
                    .model_dump_json()
                    .encode(),
                    max_bytes=100000,
                    deadline=deadline,
                )

        before = capture_validation_rng()
        with ThreadPoolExecutor(max_workers=1) as pool:
            completion = pool.submit(acknowledge)
            kwargs = {
                "model": peers[0],
                "objective": peers[1],
                "data_path": SimpleNamespace(
                    validation_dataset=lambda *_: TensorDataset(x, y)
                ),
                "scope": object(),
                "data_dir": "synthetic",
                "progress": progress,
            }
            if bad_ack:
                with pytest.raises(ValueError, match="acknowledgement"):
                    execute_admitted_epoch(request, **kwargs)
            else:
                result = execute_admitted_epoch(request, **kwargs)
                assert result.r3 == pytest.approx(
                    torch.nn.functional.smooth_l1_loss(x * 3, y).item()
                )
                assert result.rows == 7 and progress.rows == 7
                assert events == [3, 3, 1]
                assert peers[0].training and peers[1].training
            completion.result(timeout=2)
        assert capture_validation_rng() == before
    finally:
        server.close()
        client.close()
        for process in processes:
            process.stdin.close()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            process.stdout.close()
            process.stderr.close()
