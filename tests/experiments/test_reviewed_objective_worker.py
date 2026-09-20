"""Worker executes reviewed source/config with numeric state, not a module pickle."""

import pytest
import torch
from agent.schemas.data_analysis.common import canonical_sha256

from experiments.shared.objective_numerical_review import (
    NumericalReviewRequest,
    NumericalReviewResult,
)
from experiments.shared.objective_purpose_review import ObjectiveReviewMaterial
from experiments.shared.objective_review_pipeline import review_objective
from experiments.shared.reviewed_objective_worker import restore_reviewed_objective

SOURCE = """import torch
from pydantic import BaseModel
class Config(BaseModel):
    denominator: float = 1.0
class Loss(torch.nn.Module):
    def __init__(self,config):
        super().__init__()
        self.denominator=config.denominator
        self.register_buffer("scale",torch.tensor(1.0))
    def forward(self,p,t):
        return ((p-t)**2).mean()*self.scale/self.denominator
PLUGIN_LOSS_TYPE="reviewed_fixture"
PLUGIN_LOSS_CONFIG_CLASS=Config
PLUGIN_LOSS_CLASS=Loss
"""


def bundle():
    material = ObjectiveReviewMaterial(
        sources={"loss.py": SOURCE},
        effective_parameters={"denominator": 2.0},
        dependency_declaration="synthetic runtime",
    )
    request = NumericalReviewRequest(
        source=SOURCE,
        loss_name="reviewed_fixture",
        parameters={"denominator": 2.0},
        prediction={"shape": [1], "dtype": "float32", "values": [0.0]},
        target={"shape": [1], "dtype": "float32", "values": [1.0]},
    )

    class Gateway:
        def generate(self, *args, **kwargs):
            return {"decision": "approved", "reason": "synthetic trusted fixture"}

    def worker(req):
        return NumericalReviewResult(
            request_sha256=canonical_sha256(req),
            passed=True,
            reason="synthetic fixture",
            seconds=0.01,
        )

    return review_objective(
        material,
        request,
        run_id="run-1",
        review_id="review-1",
        policy_sha256="a" * 64,
        allowed_import_roots=frozenset({"torch", "pydantic"}),
        numerical_worker=worker,
        gateway=Gateway(),
    )


def test_approved_source_uses_effective_parameters_and_exact_numeric_epoch_state():
    approved = bundle()
    objective = restore_reviewed_objective(
        approved,
        expected_policy_sha256="a" * 64,
        expected_objective_sha256=approved.material.sha256,
        state={"scale": torch.tensor(3.0)},
        training=False,
        device=torch.device("cpu"),
    )
    assert objective(torch.zeros(2), torch.ones(2)).item() == 1.5
    assert objective.training is False


@pytest.mark.parametrize("change", ["policy", "objective", "source", "evidence"])
def test_unmatched_review_refuses_before_plugin_import(change, monkeypatch):
    approved = bundle()
    policy = "b" * 64 if change == "policy" else "a" * 64
    identity = "b" * 64 if change == "objective" else approved.material.sha256
    if change == "source":
        approved.numerical_request.__dict__["source"] = (
            'raise RuntimeError("must not execute")'
        )
    if change == "evidence":
        approved.evidence[0].payload["changed"] = "invalidates evidence"

    def forbidden(*args, **kwargs):
        raise AssertionError("unapproved plugin reached import")

    monkeypatch.setattr(
        "experiments.shared.reviewed_objective_worker.load_loss_plugin_from_path",
        forbidden,
    )
    with pytest.raises(ValueError):
        restore_reviewed_objective(
            approved,
            expected_policy_sha256=policy,
            expected_objective_sha256=identity,
            state={},
            training=True,
            device=torch.device("cpu"),
        )


@pytest.mark.parametrize("transport", ["json", "memfd"])
def test_cli_worker_reuses_one_module_for_multiple_calls(tmp_path, transport):
    import os
    import subprocess
    import sys
    import time
    from contextlib import ExitStack
    from pathlib import Path

    from pydantic import TypeAdapter

    from experiments.shared.reviewed_objective_worker import ObjectiveWorkerConfig
    from experiments.shared.validation_module_peer import ModulePeer
    from experiments.shared.validation_module_protocol import TensorPayload
    from experiments.shared.validation_snapshot import sealed_tensor_state

    approved = bundle()
    review_path = tmp_path / "review.json"
    review_path.write_text(approved.model_dump_json())
    state_path = tmp_path / "state.json"
    state_path.write_bytes(
        TypeAdapter(dict[str, TensorPayload]).dump_json(
            {
                "scale": TensorPayload.capture(torch.tensor(3.0)),
            }
        )
    )
    with ExitStack() as resources:
        snapshot = (
            resources.enter_context(
                sealed_tensor_state({"scale": torch.tensor(3.0)}, max_tensor_bytes=4)
            )
            if transport == "memfd"
            else None
        )
        config = ObjectiveWorkerConfig(
            bundle=review_path,
            state=state_path if snapshot is None else None,
            state_fd=snapshot.fd if snapshot is not None else None,
            policy_sha256="a" * 64,
            objective_sha256=approved.material.sha256,
            training=True,
            device="cpu",
            deadline_epoch=time.time() + 20,
            max_frame_bytes=1048576,
        )
        config_path = tmp_path / "config.json"
        config_path.write_text(config.model_dump_json())
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-m",
                "experiments.shared.reviewed_objective_worker",
                "--config",
                str(config_path),
            ],
            pass_fds=(snapshot.fd,) if snapshot is not None else (),
            cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
        )
        try:
            assert process.stdin is not None and process.stdout is not None
            peer = ModulePeer(
                input_fd=process.stdin.fileno(),
                output_fd=process.stdout.fileno(),
                device=torch.device("cpu"),
                deadline=time.monotonic() + 20,
                max_frame_bytes=1048576,
            )
            peer.train(False)
            for _ in range(10):
                assert peer(torch.zeros(2), torch.ones(2)).item() == 1.5
                assert peer.training is False
                assert process.poll() is None
            assert peer.state_dict()["scale"].item() == 3.0
            process.stdin.close()
            assert process.wait(timeout=5) == 0
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()


@pytest.mark.parametrize("sources", [{}, {"state": "state.json", "state_fd": 3}])
def test_worker_refuses_missing_or_ambiguous_epoch_state(sources):
    """Removing the cross-field check permits absent state or silent precedence."""
    from experiments.shared.reviewed_objective_worker import ObjectiveWorkerConfig

    with pytest.raises(ValueError, match="exactly one state source"):
        ObjectiveWorkerConfig(
            bundle="review.json",
            policy_sha256="a" * 64,
            objective_sha256="b" * 64,
            training=False,
            device="cpu",
            deadline_epoch=1.0,
            max_frame_bytes=1024,
            **sources,
        )


@pytest.mark.parametrize("abort", [False, True])
def test_launcher_runs_both_epoch_workers_and_reaps_after_body_failure(tmp_path, abort):
    """Catch wrong worker routing/state FD and children left alive on exceptions."""
    import hashlib
    import inspect
    import os
    import sys
    import time
    from contextlib import ExitStack
    from pathlib import Path

    from ml_models import models_sandbox
    from ml_models.models_format_sandbox import AEConfig

    from experiments.shared.epoch_model_worker import (
        EpochModelSpecification,
        EpochModelWorkerConfig,
    )
    from experiments.shared.reviewed_objective_worker import ObjectiveWorkerConfig
    from experiments.shared.validation_snapshot import sealed_tensor_state
    from experiments.shared.validation_worker_process import launch_validation_worker

    approved = bundle()
    review_path = tmp_path / "review.json"
    review_path.write_text(approved.model_dump_json())
    cfg = AEConfig(segmentation_size=1000, latent_dims=[2])
    model = models_sandbox.AE(cfg, loss_type="smooth_l1").eval()
    spec = EpochModelSpecification(
        model_type="fcnet",
        configuration=cfg.model_dump(),
        loss_type="smooth_l1",
        constructor_sha256=models_sandbox.registered_model_construction_implementation_sha256(),
        source_sha256=hashlib.sha256(
            Path(inspect.getfile(type(model))).read_bytes()
        ).hexdigest(),
    )
    pids = []
    try:
        with ExitStack() as stack:
            model_state = stack.enter_context(
                sealed_tensor_state(model.state_dict(), max_tensor_bytes=100000)
            )
            loss_state = stack.enter_context(
                sealed_tensor_state({"scale": torch.tensor(3.0)}, max_tensor_bytes=4)
            )
            common = {
                "training": False,
                "device": "cpu",
                "deadline_epoch": time.time() + 20,
                "max_frame_bytes": 100000,
            }
            configs = [
                EpochModelWorkerConfig(
                    specification=spec,
                    state_fd=model_state.fd,
                    max_snapshot_bytes=100000,
                    **common,
                ),
                ObjectiveWorkerConfig(
                    bundle=review_path,
                    state_fd=loss_state.fd,
                    policy_sha256="a" * 64,
                    objective_sha256=approved.material.sha256,
                    **common,
                ),
            ]
            workers = []
            for index, config in enumerate(configs):
                worker = stack.enter_context(
                    launch_validation_worker(
                        config,
                        python=Path(sys.executable),
                        cwd=Path(__file__).resolve().parents[2],
                        config_path=tmp_path / f"worker-{index}.json",
                        stderr_path=tmp_path / f"worker-{index}.stderr",
                        environment={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
                        confinement_prefix=(),
                    )
                )
                workers.append(worker)
                pids.append(worker.pid)
                assert worker.startup_seconds > 0
            x = torch.randn(2, 1000)
            target = torch.zeros_like(x)
            for _ in range(2):
                output = workers[0].peer(x)
                torch.testing.assert_close(output, model(x))
                actual = workers[1].peer(output, target)
                torch.testing.assert_close(
                    actual, ((model(x) - target) ** 2).mean() * 1.5
                )
            if abort:
                raise RuntimeError("synthetic coordinator failure")
    except RuntimeError as error:
        assert abort and str(error) == "synthetic coordinator failure"
    assert len(pids) == 2 and len(set(pids)) == 2
    for pid in pids:
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    for index in range(2):
        assert (tmp_path / f"worker-{index}.stderr").stat().st_mode & 0o777 == 0o600
