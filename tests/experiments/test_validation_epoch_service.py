"""Real socket transactions guard admission-before-execution and private errors."""

import socket
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import torch
from execute_tools.validation_execution import (
    CompletedTrainingEpoch,
    ValidationCallbacks,
    ValidationExecutionRequest,
    ValidationExecutionResult,
)
from ml_models.models_format_sandbox import LossConfig
from pydantic import BaseModel

from experiments.shared.inherited_validation_client import (
    InheritedClientSettings,
    InheritedValidationClient,
)
from experiments.shared.validation_epoch_service import (
    AdmittedValidationWorkload,
    serve_validation_epoch,
)


class ModelConfig(BaseModel):
    model_type: str = "synthetic"
    width: int = 1


@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "variable_steps",
        "wrong_steps",
        "wrong_config",
        "wrong_epoch",
        "failure",
    ],
)
def test_epoch_service_checks_launch_before_execution_and_sanitizes_errors(mode):
    server, client_socket = socket.socketpair()
    deadline = time.monotonic() + 10
    client = InheritedValidationClient(
        InheritedClientSettings(
            channel_fd=client_socket.detach(),
            deadline_epoch=time.time() + 10,
            max_metadata_bytes=100000,
            max_state_bytes=10000,
        ),
        serialize_scope=lambda _: "admitted synthetic scope",
        declare_rows=lambda _: 3,
    )
    workload = AdmittedValidationWorkload(
        model_type="synthetic",
        configuration=ModelConfig().model_dump(),
        model_io=None,
        loss=LossConfig(loss_type="smooth_l1"),
        scope_payload="admitted synthetic scope",
        device="cpu",
        batch_size=2,
        expected_rows=3,
        max_epochs=2,
        optimizer_steps_per_epoch=None if mode == "variable_steps" else 1,
    )
    calls = []

    def execute(request, snapshots, progress):
        calls.append(request.sequence)
        assert len(snapshots) == 2
        if mode == "failure":
            raise RuntimeError("PRIVATE target detail must never reach client")
        progress.feed(1.0, elapsed_ms=2.0)
        progress.feed(1.0, elapsed_ms=1.0)
        return ValidationExecutionResult(r3=1.25, rows=3)

    def serve():
        sequence = 0
        for _ in range(2 if mode in ("success", "variable_steps") else 1):
            sequence = serve_validation_epoch(
                server,
                workload=workload,
                sequence=sequence,
                execute=execute,
                deadline=deadline,
                max_metadata_bytes=100000,
                max_snapshot_bytes=10000,
            )
        return sequence

    model = torch.nn.Linear(1, 1)
    criterion = torch.nn.SmoothL1Loss()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(serve)
            for epoch in range(2 if mode in ("success", "variable_steps") else 1):
                request = ValidationExecutionRequest(
                    model=model,
                    criterion=criterion,
                    model_type="synthetic",
                    configuration=ModelConfig(width=2 if mode == "wrong_config" else 1),
                    completed_training=CompletedTrainingEpoch(
                        completed_epochs=9 if mode == "wrong_epoch" else epoch + 1,
                        optimizer_steps=(epoch + 2)
                        if mode in ("variable_steps", "wrong_steps")
                        else 1,
                    ),
                    model_io=None,
                    loss=workload.loss,
                    scope=object(),
                    device=torch.device("cpu"),
                    batch_size=2,
                    expected_rows=3,
                )
                callbacks = ValidationCallbacks(None, None, None)
                if mode in ("success", "variable_steps"):
                    assert client.observe(request, callbacks).r3 == 1.25
                else:
                    code = "validation_failed" if mode == "failure" else "not_admitted"
                    with pytest.raises(
                        RuntimeError, match=f"^validation refused: {code}$"
                    ):
                        client.observe(request, callbacks)
            if mode in ("success", "variable_steps"):
                assert future.result(timeout=2) == 2
                assert calls == [0, 1]
            else:
                with pytest.raises((ValueError, RuntimeError)):
                    future.result(timeout=2)
                assert calls == ([0] if mode == "failure" else [])
    finally:
        client.close()
        server.close()
