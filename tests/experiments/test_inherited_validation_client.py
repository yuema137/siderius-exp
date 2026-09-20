import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import torch
from execute_tools.validation_execution import (
    CompletedTrainingEpoch,
    ValidationCallbacks,
    ValidationExecutionRequest,
)
from ml_models.models_format_sandbox import LossConfig
from pydantic import BaseModel

from experiments.shared.validation_client_factory import create_validation_client
from experiments.shared.validation_rng import CudaRngState, capture_validation_rng

SERVER = """
import os,socket,sys,time,torch
from experiments.shared.validation_descriptor_transport import receive_snapshots
from experiments.shared.validation_epoch_protocol import ValidationEpochMetadata,ValidationBatchProgress,ValidationContinue,ValidationEpochResult,ValidationEpochRefusal
from experiments.shared.validation_frames import read_frame,write_frame
from execute_tools.validation_execution import ValidationExecutionResult
s=socket.socket(fileno=int(sys.argv[1]));mode=sys.argv[2];device=sys.argv[3]
deadline=time.monotonic()+15
def send(message):
    write_frame(s.fileno(),message.model_dump_json().encode(),max_bytes=100000,deadline=deadline)
for epoch in range(2 if mode=='success' else 1):
    with receive_snapshots(s,deadline=deadline,max_metadata_bytes=100000,max_snapshot_bytes=10000) as (payload,fds):
        request=ValidationEpochMetadata.model_validate_json(payload)
        assert request.device==device
        assert tuple(x.device for x in request.rng.torch_cuda)==((3,) if device=='cuda:3' else ())
        assert request.completed_training.completed_epochs==epoch+1
        assert request.configuration['model_type']=='synthetic_linear'
        if mode=='refusal':
            send(ValidationEpochRefusal(sequence=request.sequence,code='not_admitted'));break
        # Synthetic service+worker fixture only: no private data or candidate code.
        model=torch.nn.Linear(1,1)
        with os.fdopen(os.dup(fds[0]),'rb') as stream:
            model.load_state_dict(torch.load(stream,weights_only=True))
        total=0
        for rows,x in [(2,torch.tensor([[1.],[2.]])),(1,torch.tensor([[4.]]))]:
            total+=rows*torch.nn.functional.smooth_l1_loss(model(x),x*2).item()
            sequence=request.sequence+1 if mode=='sequence' else request.sequence
            send(ValidationBatchProgress(sequence=sequence,rows=rows,elapsed_ms=4.0))
            if mode=='sequence': break
            ack=ValidationContinue.model_validate_json(read_frame(s.fileno(),max_bytes=100000,deadline=deadline))
            assert ack.sequence==request.sequence
        if mode=='sequence': break
        send(ValidationEpochResult(sequence=request.sequence,result=ValidationExecutionResult(r3=total/3,rows=3)))
s.close()
"""


class Config(BaseModel):
    model_type: str = "synthetic_linear"


@pytest.mark.parametrize(
    "mode,implicit_cuda",
    [("success", False), ("success", True), ("refusal", False), ("sequence", False)],
)
def test_actual_epoch_exchange_and_callback_order(mode, implicit_cuda, monkeypatch):
    if implicit_cuda:
        # Wire-format regression only: no CUDA execution is claimed by this CPU test.
        monkeypatch.setattr(torch.cuda, "current_device", lambda: 3)

        def synthetic_cuda_rng(*, cuda_devices):
            assert cuda_devices == (3,)
            return capture_validation_rng().model_copy(
                update={"torch_cuda": (CudaRngState(device=3, state=b"synthetic"),)}
            )

        monkeypatch.setattr(
            "experiments.shared.inherited_validation_client.capture_validation_rng",
            synthetic_cuda_rng,
        )
    parent, child = socket.socketpair()
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            SERVER,
            str(child.fileno()),
            mode,
            "cuda:3" if implicit_cuda else "cpu",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
        pass_fds=(child.fileno(),),
    )
    child.close()
    task = ModuleType("synthetic_client_task")
    task.rows = lambda _: 3
    monkeypatch.setitem(sys.modules, task.__name__, task)
    monkeypatch.setattr(
        "experiments.shared.validation_client_factory.resolve_bound_task_data_path",
        lambda: task,
    )
    monkeypatch.setattr(
        "experiments.shared.validation_client_factory.resolve_task_scope_capability",
        lambda value: (
            SimpleNamespace(serialize_scope=lambda _: "synthetic scope")
            if value is task
            else None
        ),
    )
    client = create_validation_client(
        {
            "row_declaration": "synthetic_client_task:rows",
            "channel_fd": parent.detach(),
            "deadline_epoch": time.time() + 15,
            "max_metadata_bytes": 100000,
            "max_state_bytes": 10000,
        }
    )
    model = torch.nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    criterion = torch.nn.SmoothL1Loss()
    events = []
    try:
        for epoch in range(2 if mode == "success" else 1):
            x = torch.tensor([[1.0], [2.0], [4.0]])
            optimizer.zero_grad()
            criterion(model(x), x * 2).backward()
            optimizer.step()
            state = {k: v.clone() for k, v in model.state_dict().items()}
            request = ValidationExecutionRequest(
                model=model,
                criterion=criterion,
                model_type="synthetic_linear",
                configuration=Config(),
                completed_training=CompletedTrainingEpoch(
                    completed_epochs=epoch + 1, optimizer_steps=1
                ),
                model_io=None,
                loss=LossConfig(loss_type="smooth_l1"),
                scope=object(),
                device=torch.device("cuda" if implicit_cuda else "cpu"),
                batch_size=2,
                expected_rows=3,
            )
            verifier = SimpleNamespace(
                is_terminal=True, feed=lambda *a, **k: events.append("feed")
            )
            callbacks = ValidationCallbacks(
                verifier=verifier,
                on_verified=lambda: events.append("verified"),
                check_allocation=lambda: events.append("allocation"),
            )
            if mode == "success":
                result = client.observe(request, callbacks)
                assert result.r3 == pytest.approx(
                    criterion(model(x), x * 2).item(), abs=1e-6
                )
                assert result.rows == 3
                assert model.training and criterion.training
                assert all(
                    torch.equal(state[k], v) for k, v in model.state_dict().items()
                )
            else:
                with pytest.raises((RuntimeError, ValueError)):
                    client.observe(request, callbacks)
                with pytest.raises(RuntimeError, match="closed"):
                    client.observe(request, callbacks)
        assert process.wait(timeout=5) == 0
        if mode == "success":
            assert [e for e in events if e != "allocation"] == ["feed", "verified"] * 2
    finally:
        client.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
