"""Native estimator behind actual epoch transport and two numeric subprocesses.

Synthetic task/admission inputs only. This proves composition, not protected
launcher provenance, production confinement or real-task deployment.
"""

import hashlib
import inspect
import os
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from execute_tools.validation_execution import (
    CompletedTrainingEpoch,
    ValidationCallbacks,
    ValidationExecutionRequest,
)
from ml_models import models_sandbox
from ml_models.loss_models_sandbox import get_criterion
from ml_models.models_format_sandbox import AEConfig, LossConfig
from torch.utils.data import TensorDataset

from experiments.shared.builtin_objective_worker import BuiltinObjectiveWorkerConfig
from experiments.shared.epoch_model_worker import (
    EpochModelSpecification,
    EpochModelWorkerConfig,
)
from experiments.shared.inherited_validation_client import (
    InheritedClientSettings,
    InheritedValidationClient,
)
from experiments.shared.validation_epoch_execution import execute_admitted_epoch
from experiments.shared.validation_epoch_service import (
    AdmittedValidationWorkload,
    serve_validation_epoch,
)
from experiments.shared.validation_worker_process import launch_validation_worker


def test_two_training_epochs_through_transport_workers_and_native_estimator(
    tmp_path, record_property
):
    cfg = AEConfig(segmentation_size=1000, latent_dims=[2])
    model = models_sandbox.AE(cfg, loss_type="smooth_l1")
    loss_cfg = LossConfig(loss_type="smooth_l1", beta=0.7)
    criterion = get_criterion(loss_cfg)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.001)
    x = torch.randn(7, 1000)
    y = x * 0.5
    spec = EpochModelSpecification(
        model_type="fcnet",
        configuration=cfg.model_dump(mode="json"),
        loss_type="smooth_l1",
        constructor_sha256=models_sandbox.registered_model_construction_implementation_sha256(),
        source_sha256=hashlib.sha256(
            Path(inspect.getfile(type(model))).read_bytes()
        ).hexdigest(),
    )
    loss_source = hashlib.sha256(
        Path(inspect.getfile(get_criterion)).read_bytes()
    ).hexdigest()
    workload = AdmittedValidationWorkload(
        model_type="fcnet",
        configuration=cfg.model_dump(mode="json"),
        model_io=None,
        loss=loss_cfg,
        scope_payload="synthetic fixed validation",
        device="cpu",
        batch_size=3,
        expected_rows=7,
        max_epochs=2,
        optimizer_steps_per_epoch=1,
    )
    server, client_socket = socket.socketpair()
    deadline_epoch = time.time() + 25
    deadline = time.monotonic() + 25
    client = InheritedValidationClient(
        InheritedClientSettings(
            channel_fd=client_socket.detach(),
            deadline_epoch=deadline_epoch,
            max_metadata_bytes=100000,
            max_state_bytes=100000,
        ),
        serialize_scope=lambda _: "synthetic fixed validation",
        declare_rows=lambda _: 7,
    )
    timings = []
    pids = []

    def execute(request, snapshots, progress):
        common = {
            "training": True,
            "device": "cpu",
            "deadline_epoch": deadline_epoch,
            "max_frame_bytes": 1000000,
        }
        configs = [
            EpochModelWorkerConfig(
                specification=spec,
                state_fd=snapshots[0],
                max_snapshot_bytes=100000,
                **common,
            ),
            BuiltinObjectiveWorkerConfig(
                loss=loss_cfg,
                source_sha256=loss_source,
                state_fd=snapshots[1],
                max_snapshot_bytes=100000,
                **common,
            ),
        ]
        with ExitStack() as stack:
            workers = []
            for role, config in zip(("model", "objective"), configs, strict=True):
                worker = stack.enter_context(
                    launch_validation_worker(
                        config,
                        python=Path(sys.executable),
                        cwd=Path(__file__).resolve().parents[2],
                        config_path=tmp_path / f"{request.sequence}-{role}.json",
                        stderr_path=tmp_path / f"{request.sequence}-{role}.stderr",
                        environment={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
                        confinement_prefix=(),
                    )
                )
                workers.append(worker)
                pids.append(worker.pid)
            started = time.perf_counter()
            result = execute_admitted_epoch(
                request,
                model=workers[0].peer,
                objective=workers[1].peer,
                data_path=SimpleNamespace(
                    validation_dataset=lambda *_: TensorDataset(x, y)
                ),
                scope=object(),
                data_dir="synthetic",
                progress=progress,
            )
            timings.append(
                {
                    "epoch": request.sequence + 1,
                    "model_startup": workers[0].startup_seconds,
                    "objective_startup": workers[1].startup_seconds,
                    "validation": time.perf_counter() - started,
                }
            )
            return result

    def serve():
        sequence = 0
        for _ in range(2):
            sequence = serve_validation_epoch(
                server,
                workload=workload,
                sequence=sequence,
                execute=execute,
                deadline=deadline,
                max_metadata_bytes=100000,
                max_snapshot_bytes=100000,
            )
        return sequence

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(serve)
            for epoch in range(2):
                optimizer.zero_grad()
                criterion(model(x), y).backward()
                optimizer.step()
                before = {
                    name: value.clone() for name, value in model.state_dict().items()
                }
                request = ValidationExecutionRequest(
                    model=model,
                    criterion=criterion,
                    model_type="fcnet",
                    configuration=cfg,
                    completed_training=CompletedTrainingEpoch(
                        completed_epochs=epoch + 1, optimizer_steps=1
                    ),
                    model_io=None,
                    loss=loss_cfg,
                    scope=object(),
                    device=torch.device("cpu"),
                    batch_size=3,
                    expected_rows=7,
                )
                result = client.observe(request, ValidationCallbacks(None, None, None))
                with torch.no_grad():
                    expected = (
                        sum(
                            len(batch) * criterion(model(batch), target).item()
                            for batch, target in zip(
                                x.split(3), y.split(3), strict=True
                            )
                        )
                        / 7
                    )
                assert result.r3 == pytest.approx(expected, abs=1e-6)
                assert result.rows == 7 and model.training
                assert all(
                    torch.equal(before[name], value)
                    for name, value in model.state_dict().items()
                )
            assert future.result(timeout=2) == 2
        assert len(pids) == 4
        for pid in pids:
            with pytest.raises(ProcessLookupError):
                os.kill(pid, 0)
        record_property("epoch_timings", timings)
    finally:
        client.close()
        server.close()
