import hashlib
import inspect
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import torch
from core.local_code import CodePackageDeclaration, MemberIdentity, capture_package
from ml_models import models_sandbox
from ml_models.models_format_sandbox import AEConfig

from experiments.shared.epoch_model_worker import (
    EpochModelSource,
    EpochModelSpecification,
    EpochModelWorkerConfig,
    StagedModelPackage,
    restore_epoch_model,
)
from experiments.shared.native_training_metadata import (
    NativeConfigurationMetadata,
    NativeConfigurationRequest,
)
from experiments.shared.validation_code_snapshot import stage_validation_code
from experiments.shared.validation_module_peer import ModulePeer
from experiments.shared.validation_snapshot import sealed_tensor_state

SOURCE = """import torch
from pydantic import BaseModel
class Config(BaseModel):
    model_type: str = "epoch_fixture"
    factor: float = 2.0
class Model(torch.nn.Module):
    def __init__(self, config, *, loss_type):
        super().__init__()
        assert loss_type == "smooth_l1"
        self.factor = config.factor
        self.scale = torch.nn.Parameter(torch.tensor(0.0))
    def forward(self,x):
        return x*self.scale*self.factor
PLUGIN_MODEL_TYPE="epoch_fixture"
PLUGIN_OUTPUT_TYPE="regressor"
PLUGIN_CONFIG_CLASS=Config
PLUGIN_MODEL_CLASS=Model
"""


def specification():
    return EpochModelSpecification(
        model_type="epoch_fixture",
        configuration={"model_type": "epoch_fixture", "factor": 2.0},
        loss_type="smooth_l1",
        constructor_sha256=models_sandbox.registered_model_construction_implementation_sha256(),
        source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        plugin_source=SOURCE,
    )


def config(spec, fd):
    return EpochModelWorkerConfig(
        specification=spec,
        state_fd=fd,
        max_snapshot_bytes=100000,
        training=True,
        device="cpu",
        deadline_epoch=time.time() + 15,
        max_frame_bytes=100000,
    )


def _package_spec(tmp_path):
    research = tmp_path / "research"
    research.mkdir()
    source = "from .ops import transform\n" + SOURCE.replace(
        "return x*self.scale*self.factor", "return transform(x)*self.scale*self.factor"
    )
    (research / "model.py").write_text(source)
    (research / "ops.py").write_text("def transform(x):\n    return x * 1.5\n")
    captured = capture_package(
        CodePackageDeclaration(root=".", files=("model.py", "ops.py")), research
    )
    parent = tmp_path / "operator"
    parent.mkdir(mode=0o700)
    staged = stage_validation_code(captured, parent=parent, owner_uid=os.geteuid())
    # The worker must use captured dependencies rather than mutable research paths.
    (research / "ops.py").write_text(
        "raise AssertionError('mutable research imported')\n"
    )
    spec = specification().model_copy(
        update={
            "plugin_source": None,
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "plugin_package": StagedModelPackage(
                root=staged.root,
                identity=MemberIdentity(package=staged.identity, member="model.py"),
            ),
        }
    )
    return spec


@pytest.mark.parametrize("packaged", [False, True])
def test_real_worker_restores_epoch_without_final_artifact(tmp_path, packaged):
    spec = _package_spec(tmp_path) if packaged else specification()
    with sealed_tensor_state(
        {"scale": torch.tensor(3.0)}, max_tensor_bytes=4
    ) as snapshot:
        path = tmp_path / "worker.json"
        path.write_text(config(spec, snapshot.fd).model_dump_json())
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "experiments.shared.epoch_model_worker",
                "--config",
                str(path),
            ],
            cwd=Path(__file__).resolve().parents[2],
            env={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
            pass_fds=(snapshot.fd,),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            peer = ModulePeer(
                input_fd=process.stdin.fileno(),
                output_fd=process.stdout.fileno(),
                device=torch.device("cpu"),
                deadline=time.monotonic() + 10,
                max_frame_bytes=100000,
            )
            for _ in range(3):
                assert peer(torch.tensor([2.0])).item() == (18.0 if packaged else 12.0)
                assert peer.training
            process.stdin.close()
            assert process.wait(timeout=3) == 0
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()


def test_changed_package_dependency_refuses_before_import(tmp_path):
    spec = _package_spec(tmp_path)
    helper = spec.plugin_package.root / "ops.py"
    helper.chmod(0o644)
    helper.write_text("raise AssertionError('changed dependency imported')\n")
    with (
        sealed_tensor_state(
            {"scale": torch.tensor(3.0)}, max_tensor_bytes=4
        ) as snapshot,
        pytest.raises(ValueError, match="package differs"),
        restore_epoch_model(config(spec, snapshot.fd)),
    ):
        pytest.fail("changed package restored")


def test_metadata_child_uses_plugin_schema_without_constructing_model():
    source = (
        SOURCE.replace(
            "self.scale = torch.nn.Parameter(torch.tensor(0.0))",
            "raise AssertionError('model allocated during metadata resolution')",
        )
        + "\nprint('candidate stdout noise')\n"
    )
    selected = EpochModelSource(
        model_type="epoch_fixture",
        constructor_sha256=models_sandbox.registered_model_construction_implementation_sha256(),
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        plugin_source=source,
    )
    request = NativeConfigurationRequest(
        source=selected,
        model_parameters={"model_type": "epoch_fixture", "factor": "3.5"},
        training={"epochs": 2},
        loss={"loss_type": "smooth_l1"},
    )
    process = subprocess.run(
        [sys.executable, "-m", "experiments.shared.native_training_metadata"],
        input=request.model_dump_json(),
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[2],
        env={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
        timeout=10,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    result = NativeConfigurationMetadata.model_validate_json(process.stdout)
    assert result.model.configuration == {"model_type": "epoch_fixture", "factor": 3.5}
    assert result.model.loss_type == "smooth_l1"
    assert result.model.source_sha256 == selected.source_sha256
    assert result.training.epochs == 2 and result.training.device == "cuda"
    assert "candidate stdout noise" in process.stderr


@pytest.mark.parametrize("fault", ["source", "constructor", "state"])
def test_mismatched_epoch_material_refuses(fault):
    spec = specification()
    if fault == "source":
        spec = spec.model_copy(
            update={"plugin_source": "raise AssertionError('must not import')"}
        )
    if fault == "constructor":
        spec = spec.model_copy(update={"constructor_sha256": "0" * 64})
    state = (
        {"other": torch.tensor(3.0)}
        if fault == "state"
        else {"scale": torch.tensor(3.0)}
    )
    with (
        sealed_tensor_state(state, max_tensor_bytes=4) as snapshot,
        pytest.raises((ValueError, RuntimeError)),
        restore_epoch_model(config(spec, snapshot.fd)),
    ):
        pytest.fail("mismatch restored")


def test_builtin_uses_exact_native_config_and_source():
    cfg = AEConfig(segmentation_size=1000, latent_dims=[2])
    model = models_sandbox.AE(cfg, loss_type="smooth_l1")
    spec = EpochModelSpecification(
        model_type="fcnet",
        configuration=cfg.model_dump(),
        loss_type="smooth_l1",
        constructor_sha256=models_sandbox.registered_model_construction_implementation_sha256(),
        source_sha256=hashlib.sha256(
            Path(inspect.getfile(type(model))).read_bytes()
        ).hexdigest(),
    )
    with (
        sealed_tensor_state(model.state_dict(), max_tensor_bytes=100000) as snapshot,
        restore_epoch_model(config(spec, snapshot.fd)) as restored,
    ):
        x = torch.randn(2, 1000)
        torch.testing.assert_close(restored(x), model(x), rtol=0, atol=0)
