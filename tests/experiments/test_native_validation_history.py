"""Actual native child training records worker-backed validation in its history.

Synthetic HDF5 only; this does not establish launcher authorization or OS isolation.
"""

import hashlib
import inspect
import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import asdict, replace
from pathlib import Path

import execute_tools.train_engine_sandbox as native
import h5py
import numpy as np
import pytest
from core.local_code import CodePackageDeclaration, capture_package
from execute_tools.dataset_config import DataScope, DatasetProfile
from execute_tools.scope_artifact import write_scope_artifact
from execute_tools.training_history import interpret_training_results
from execute_tools.validation_execution import ValidationDeployment
from ml_models import models_sandbox
from ml_models.loss_models_sandbox import get_criterion
from ml_models.models_format_sandbox import AEConfig, LossConfig

from experiments.shared.epoch_model_worker import (
    EpochModelSpecification,
)
from experiments.shared.native_job_admission import (
    NativeReviewedObjective,
    admit_native_job,
)
from experiments.shared.native_loss_discovery import LossDiscoveryRequest
from experiments.shared.native_model_discovery import ModelDiscoveryRequest
from experiments.shared.native_objective_metadata import (
    ObjectiveMetadataRequest,
)
from experiments.shared.native_training_inputs import capture_native_training_inputs
from experiments.shared.objective_numerical_review import (
    NumericalReviewRequest,
)
from experiments.shared.objective_purpose_review import ObjectiveReviewMaterial
from experiments.shared.validation_admission import review_native_objective_once
from experiments.shared.validation_admission_process import AdmissionProbeRuntime
from experiments.shared.validation_code_snapshot import (
    bind_discovered_loss_package,
    bind_discovered_model_source,
    stage_validation_code,
)
from experiments.shared.validation_confinement import (
    NamespaceMount,
    ValidationNamespace,
)
from experiments.shared.validation_epoch_service import (
    AdmittedValidationWorkload,
)
from experiments.shared.validation_training_execution import (
    AdmittedEpochExecutor,
    EpochWorkerRuntime,
    ReviewedEpochObjective,
    run_admitted_native_training,
)
from experiments.tidmad.main_orchestrator.validation_scope import (
    admit_captured_validation_scope,
)
from tasks.tidmad.runtime.profile import tidmad_topology
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope, TidmadTaskDataPath


@pytest.mark.parametrize(
    "custom,budgeted,plugin,through_handler",
    [
        (False, False, False, False),
        (True, False, False, False),
        ("package", False, False, False),
        ("package", False, True, False),
        (False, True, False, False),
        (False, False, True, False),
        pytest.param(False, False, False, True, id="handler-builtin"),
        pytest.param(False, False, False, "frozen", id="handler-frozen-adapter"),
        pytest.param(True, False, False, True, id="handler-custom"),
        pytest.param("package", False, False, True, id="handler-package"),
    ],
)
def test_native_entry_records_external_validation_history(
    tmp_path, record_property, custom, budgeted, plugin, through_handler
):
    root = Path(__file__).resolve().parents[2]
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(
        prefix="native-epoch-smoke-", dir=tmp_path
    ) as temp:
        p = Path(temp)
        admission = _admission_runtime(p)
        training = p / "training"
        validation = p / "validation"
        training.mkdir()
        validation.mkdir()
        payload = json.loads(
            (root / "tasks/tidmad/resolved/dataset_profile.json").read_text()
        )
        payload["dataset"].update(
            num_files=1, psd_segment_length=2000, segments_per_file=1
        )
        payload["anchor_selection_files"] = [0]
        payload["health_peek_files"] = [0]
        profile = DatasetProfile.model_validate(payload)
        topology = tidmad_topology(profile)
        for family, folder in [("training", training), ("validation", validation)]:
            path = folder / getattr(topology.dataset, f"{family}_file_name")(0)
            with h5py.File(path, "w") as f:
                for channel in (
                    topology.channels.input_channel,
                    topology.channels.target_channel,
                ):
                    f.create_dataset(
                        f"timeseries/{channel}/timeseries",
                        data=np.arange(2000, dtype=np.int16).astype("int8"),
                    )
        cfg = AEConfig(segmentation_size=1000, latent_dims=[2])
        configuration = cfg.model_dump(mode="json")
        plugin_source = None
        if plugin:
            configuration["model_type"] = "admitted_fcnet"
            plugin_source = 'from typing import Literal\nfrom ml_models.models_format_sandbox import AEConfig\nimport torch\nclass Config(AEConfig):\n    model_type: Literal["admitted_fcnet"] = "admitted_fcnet"\nclass Model(torch.nn.Module):\n    def __init__(self, config):\n        super().__init__()\n        self.scale=torch.nn.Parameter(torch.tensor(0.5))\n    def forward(self, x):\n        return x.float()*self.scale\nPLUGIN_MODEL_TYPE="admitted_fcnet"\nPLUGIN_CONFIG_CLASS=Config\nPLUGIN_MODEL_CLASS=Model\nPLUGIN_OUTPUT_TYPE="regressor"\n'

        approved, review, _losses, objective_metadata = (
            _custom_review(p, admission, packaged=custom == "package", regressor=plugin)
            if custom
            else (None, None, None, None)
        )
        loss = (
            LossConfig(loss_type="custom", loss_name="native_custom")
            if custom
            else LossConfig(loss_type="smooth_l1")
        )
        for name, value in [
            ("model", configuration),
            ("loss", loss.model_dump(mode="json")),
            (
                "train",
                {
                    "epochs": 1 if budgeted else 2,
                    "batch_size": 1,
                    "device": "cpu",
                    "lr": 0.001,
                    "optimizer_type": "adam",
                },
            ),
            ("profile", profile.to_wire()),
        ]:
            (p / f"{name}.json").write_text(json.dumps(value))
        adapter_id = (
            "tidmad_frozen_training_pool" if through_handler == "frozen" else "tidmad"
        )
        manifest = {
            "task_data_path": {
                "file": str(root / "tasks/tidmad/runtime/tidmad_data_path.py"),
                "symbol": "TidmadFrozenPoolDataPath"
                if through_handler == "frozen"
                else "TidmadTaskDataPath",
                "id": adapter_id,
            },
            "task_health": {"none": True},
        }
        manifest.update(
            dataset_profile={"config": str(p / "profile.json")},
            metric={
                "declaration": str(root / "tasks/tidmad/resolved/metric_spec.json"),
                "implementation": {
                    "file": str(root / "tasks/tidmad/runtime/scoring.py"),
                    "symbol": "TidmadDenoisingMetric",
                },
            },
            task_config={
                "config": str(root / "tasks/tidmad/declared/task_config.yaml")
            },
        )
        (p / "manifest.json").write_text(json.dumps(manifest))
        adapter = TidmadTaskDataPath()
        scope = TidmadScope(sample_set={0: [0]}, seg_size=1000, profile=profile)
        scope_payload = adapter.serialize_scope(scope)
        digest = write_scope_artifact(str(p / "scope.json"), scope_payload)
        spec = EpochModelSpecification(
            model_type=configuration["model_type"],
            configuration=configuration,
            loss_type=loss.loss_type,
            constructor_sha256=models_sandbox.registered_model_construction_implementation_sha256(),
            plugin_source=plugin_source,
            source_sha256=hashlib.sha256(
                plugin_source.encode()
                if plugin_source
                else Path(inspect.getfile(models_sandbox.AE)).read_bytes()
            ).hexdigest(),
        )
        staged_model = None
        if plugin_source:
            research_model = p / "model-source"
            research_model.mkdir()
            (research_model / "model.py").write_text(plugin_source)
            captured_model = capture_package(
                CodePackageDeclaration(root=".", files=("model.py",)), research_model
            )
            model_parent = p / "model-captures"
            model_parent.mkdir(mode=0o700)
            staged_model = stage_validation_code(
                captured_model, parent=model_parent, owner_uid=os.geteuid()
            )
            (research_model / "model.py").write_text(
                "raise AssertionError('mutable model imported')"
            )
            admission = replace(
                admission,
                namespace=admission.namespace.model_copy(
                    update={
                        "mounts": (
                            *admission.namespace.mounts,
                            NamespaceMount(
                                source=staged_model.root, target=staged_model.root
                            ),
                        ),
                    }
                ),
                environment={
                    **admission.environment,
                    "SIDERIUS_PLUGIN_DIRS": str(staged_model.root),
                },
            )
        discovered = admission.model_selection(
            ModelDiscoveryRequest(model_type=configuration["model_type"])
        )
        admitted_model_source = bind_discovered_model_source(
            discovered,
            package=staged_model,
            constructor_sha256=spec.constructor_sha256,
            builtin_source_sha256=hashlib.sha256(
                Path(inspect.getfile(models_sandbox.AE)).read_bytes()
            ).hexdigest(),
        )
        loss_sha = hashlib.sha256(
            Path(inspect.getfile(get_criterion)).read_bytes()
        ).hexdigest()
        workload = AdmittedValidationWorkload(
            model_type=configuration["model_type"],
            configuration=configuration,
            model_io=None,
            loss=loss,
            scope_payload=scope_payload,
            device="cpu",
            batch_size=1,
            expected_rows=2,
            max_epochs=2,
        )
        deadline_epoch = time.time() + 35
        deadline = time.monotonic() + 35
        deployment = ValidationDeployment(
            factory="experiments.shared.validation_client_factory:create_validation_client",
            settings={
                "row_declaration": "experiments.tidmad.main_orchestrator.validation_rows:declared_rows",
                "deadline_epoch": deadline_epoch,
                "max_metadata_bytes": 100000,
                "max_state_bytes": 10000000,
            },
        )
        command = [
            sys.executable,
            native.__file__,
            "--model_cfg",
            str(p / "model.json"),
            "--train_cfg",
            str(p / "train.json"),
            "--loss_cfg",
            str(p / "loss.json"),
            "--dataset_profile_json",
            str(p / "profile.json"),
            "--data_dir",
            str(training),
            "--sandbox_dir",
            str(p / "sandbox"),
            "--task_data_path_id",
            adapter_id,
            "--task_manifest",
            str(p / "manifest.json"),
            "--task_scope_ref",
            str(p / "scope.json"),
            "--task_scope_digest",
            digest,
            "--task_eval_scope_ref",
            str(p / "scope.json"),
            "--task_eval_scope_digest",
            digest,
            "--validation_requested_rows",
            "2",
            "--exp_id",
            "native_epoch",
            "--validation_executor_json",
            deployment.model_dump_json(),
        ]

        if budgeted:
            (p / "policy.json").write_text(
                json.dumps(
                    {
                        "training_budget": {
                            "budget_seconds": 120,
                            "reserve_fraction": 0.1,
                            "max_epochs": 2,
                            "started_monotonic_seconds": time.monotonic(),
                        }
                    }
                )
            )
            command.extend(
                [
                    "--runtime_policy_json",
                    str(p / "policy.json"),
                    "--runtime_observation_out",
                    str(p / "runtime.json"),
                ]
            )

        if through_handler:
            from experiments.shared.native_launcher import (
                NativeLaunchContext,
                NativeLauncherPolicy,
            )
            from experiments.shared.native_runtime import NativeRuntimePolicy
            from experiments.shared.native_runtime_review import NativeReviewPolicy
            from experiments.tidmad.main_orchestrator.native_handler import (
                TidmadNativePolicy,
                run_with_policy,
            )

            sandbox = p / "sandbox"
            sandbox.mkdir()
            jobs = p / "handler-jobs"
            jobs.mkdir(mode=0o700)
            base = _admission_runtime(p).namespace
            namespace = base.model_copy(
                update={
                    "mounts": (
                        *base.mounts,
                        NamespaceMount(source=root / "tasks", target=root / "tasks"),
                        NamespaceMount(source=p, target=p),
                    ),
                    "hidden_directories": (validation,),
                }
            )
            runtime = NativeRuntimePolicy(
                python=Path(sys.executable),
                entrypoint=Path(native.__file__),
                readable_roots=(p,),
                job_parent=jobs,
                probe_namespace=namespace,
                training_namespace=namespace.model_copy(
                    update={
                        "mounts": (
                            *namespace.mounts,
                            NamespaceMount(
                                source=sandbox, target=sandbox, mode="write"
                            ),
                        ),
                        "share_network": True,
                    }
                ),
                worker_namespace=base,
                child_environment={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
                device="cpu",
                constructor_sha256=models_sandbox.registered_model_construction_implementation_sha256(),
                builtin_model_sha256=hashlib.sha256(
                    Path(models_sandbox.__file__).read_bytes()
                ).hexdigest(),
                builtin_objective_sha256=loss_sha,
                max_snapshot_bytes=10000000,
            )
            launch_policy = NativeLauncherPolicy(
                caller_uid=os.getuid(),
                caller_gid=os.getgid(),
                cwd=root,
                handler="experiments.tidmad.main_orchestrator.native_handler:run",
                settings={},
                environment=runtime.child_environment,
                deadline_epoch=time.time() + 60,
            )
            context = NativeLaunchContext(
                caller_uid=os.getuid(),
                caller_gid=os.getgid(),
                source_cwd=root,
                deadline=time.monotonic() + 60,
                policy=launch_policy,
                source_environment={"SIDERIUS_LOSS_DIRS": str(_losses)}
                if custom
                else {},
            )
            if custom == "package":
                from core.generated_library import bind_generated_library_to_workspace
                from core.local_code import bind_code_package, package_subprocess_env

                source_environment = dict(context.source_environment)
                bind_generated_library_to_workspace(
                    str(p / "handler-transport"), environ=source_environment
                )
                code_package = capture_package(
                    CodePackageDeclaration(
                        root=".", files=("native_custom.py", "helper.py")
                    ),
                    _losses,
                )
                with bind_code_package(code_package):
                    package_subprocess_env(source_environment)
                context = replace(context, source_environment=source_environment)
            review_policy = None
            if custom:
                review_policy = NativeReviewPolicy(
                    registry=p / "registry",
                    run_id="synthetic",
                    policy_sha256="a" * 64,
                    allowed_import_roots=("torch", "pydantic"),
                    dependency_declaration="synthetic installed runtime",
                    provider="openai",
                    model_id="fixture",
                    credential_file=p / "unused-credentials",
                    credential_key="OPENAI_API_KEY",
                    long_prediction=approved.numerical_request.prediction,
                    long_target=approved.numerical_request.target,
                    float_prediction=approved.numerical_request.prediction,
                    float_target=approved.numerical_request.prediction,
                )
            task_policy = TidmadNativePolicy(
                task_data_path_id=adapter_id,
                runtime=runtime,
                manifest=p / "manifest.json",
                manifest_sha256=hashlib.sha256(
                    (p / "manifest.json").read_bytes()
                ).hexdigest(),
                profile=profile,
                allowed_scope=DataScope(file_indices=[0]),
                validation_data=validation,
                review=review_policy,
            )

            class Gateway:
                def generate(self, *args, **kwargs):
                    return {
                        "decision": "approved",
                        "reason": "synthetic fixture, not live review",
                    }

            assert (
                run_with_policy(context, tuple(command), task_policy, gateway=Gateway())
                == 0
            )
            receipt = json.loads(next(jobs.glob("*/execution.json")).read_text())
            assert receipt["result"]["validation_epochs"] == 2
            assert len(receipt["epochs"]) == 2
            assert receipt["stages_seconds"]["total"] > 0
            record_property("handler_receipt", receipt)
            return

        input_parent = p / "input-captures"
        input_parent.mkdir(mode=0o700)
        captured = capture_native_training_inputs(
            command,
            python=Path(sys.executable),
            entrypoint=Path(native.__file__),
            source_cwd=root,
            allowed_roots=(p,),
            parent=input_parent,
            owner_uid=os.geteuid(),
            max_file_bytes=1000000,
        )
        # Actual training must use admitted bytes even if research edits follow.
        (p / "model.json").write_text('{"model_type":"must_not_be_loaded"}')

        def admit_scope(metadata):
            return admit_captured_validation_scope(
                captured,
                manifest=p / "manifest.json",
                manifest_sha256=hashlib.sha256(
                    (p / "manifest.json").read_bytes()
                ).hexdigest(),
                task_data_path_id="tidmad",
                source_cwd=root,
                profile=profile,
                allowed_scope=DataScope(file_indices=[0]),
                model_segmentation_size=metadata.model.configuration[
                    "segmentation_size"
                ],
            )

        job = admit_native_job(
            captured,
            model_source=admitted_model_source,
            probe=admission,
            admit_scope=admit_scope,
            device="cpu",
            builtin_objective_sha256=loss_sha,
            reviewed=NativeReviewedObjective(
                metadata=objective_metadata,
                bundle=approved,
                worker=ReviewedEpochObjective(
                    bundle=review,
                    policy_sha256="a" * 64,
                    objective_sha256=approved.material.sha256,
                    target_dtype="long",
                ),
            )
            if custom
            else None,
        )
        plan = job.plan
        workload = plan.workload
        if custom:
            assert plan.reviewed_objective.target_dtype == (
                "float" if plugin else "long"
            )
        execute = AdmittedEpochExecutor(
            plan=plan,
            runtime=EpochWorkerRuntime(
                python=Path(sys.executable),
                cwd=root,
                environment={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
                confinement_prefix=(),
                diagnostics=p,
                deadline_epoch=deadline_epoch,
                max_frame_bytes=10000000,
                max_snapshot_bytes=10000000,
            ),
            data_path=adapter,
            data_dir=str(validation),
        )
        result = run_admitted_native_training(
            captured.command,
            loss_source=job.loss_source,
            model_source=job.model_source,
            python=Path(sys.executable),
            entrypoint=Path(native.__file__),
            deployment=deployment,
            environment={
                "PATH": os.defpath,
                "OMP_NUM_THREADS": "1",
                **({"SIDERIUS_LOSS_DIRS": str(p / "losses")} if custom else {}),
            },
            confinement_prefix=(),
            cwd=root,
            workload=workload,
            execute=execute,
            deadline=deadline,
            max_metadata_bytes=100000,
            max_snapshot_bytes=10000000,
        )
        assert result.returncode == 0 and result.validation_epochs == 2
        records = [asdict(timing) for timing in execute.timings]
        files = list((p / "sandbox").rglob("*.json"))
        histories = [
            json.loads(f.read_text())
            for f in files
            if "training_history" in json.loads(f.read_text())
        ]
        assert len(histories) == 1, files
        record_property("native_total_seconds", time.perf_counter() - started)
        history = interpret_training_results(
            histories[0], expected_validation=True
        ).history
        assert history is not None and history.epochs_completed == 2
        assert list(history.validation_objective) == [row["r3"] for row in records]
        assert history.validation_samples == history.validation_requested_samples == 2
        assert history.comparability == ("not_established" if custom else "established")
        if custom:
            assert history.comparability_reason == "custom_objective_undeclared"
        record_property("native_epoch_timings", records)


def _custom_review(p, admission, *, packaged=False, regressor=False):
    """Real confined numerical review; only the purpose verdict is synthetic."""
    source = 'import torch\nfrom pydantic import BaseModel\nclass Config(BaseModel):\n    denominator: float = 2.0\nclass Loss(torch.nn.Module):\n    def __init__(self,config):\n        super().__init__()\n        self.denominator=config.denominator\n    def forward(self,p,t):\n        return torch.nn.functional.cross_entropy(p,t)/self.denominator\nPLUGIN_LOSS_TYPE="native_custom"\nPLUGIN_LOSS_CONFIG_CLASS=Config\nPLUGIN_LOSS_CLASS=Loss\nPLUGIN_LOSS_TARGET_DTYPE="long"\n'
    losses = p / "losses"
    losses.mkdir()
    sources = {"native_custom.py": source}
    if packaged:
        source = source.replace(
            "return torch.nn.functional.cross_entropy(p,t)/self.denominator",
            "from .helper import error\n        return error(p,t)/self.denominator",
        )
        sources = {
            "native_custom.py": source,
            "helper.py": "import torch\ndef error(p,t):\n    return torch.nn.functional.cross_entropy(p,t)\n",
        }
    if regressor:
        source = source.replace(
            'PLUGIN_LOSS_TARGET_DTYPE="long"', 'PLUGIN_LOSS_TARGET_DTYPE="float"'
        )
        sources["native_custom.py"] = source
        sources["helper.py"] = "def error(p,t):\n    return ((p-t)**2).mean()\n"
    for name, content in sources.items():
        (losses / name).write_text(content)
    captured = capture_package(
        CodePackageDeclaration(root=".", files=tuple(sources)), losses
    )
    operator = p / "operator"
    operator.mkdir(mode=0o700)
    staged = stage_validation_code(captured, parent=operator, owner_uid=os.getuid())
    # The native loader must read the fixed copy, not this now-invalid research file.
    (losses / "native_custom.py").write_text(
        "raise AssertionError('mutable research source imported')\n"
    )
    losses = staged.root
    source = staged.member(losses / "native_custom.py").source.decode()
    selection_probe = replace(
        admission,
        namespace=admission.namespace.model_copy(
            update={
                "mounts": (
                    *admission.namespace.mounts,
                    NamespaceMount(source=staged.root, target=staged.root),
                )
            }
        ),
        environment={**admission.environment, "SIDERIUS_LOSS_DIRS": str(staged.root)},
    )
    selected = selection_probe.loss_selection(
        LossDiscoveryRequest(
            loss_name="native_custom",
            code_package=CodePackageDeclaration(
                root=str(staged.root), files=tuple(sources)
            ),
        )
    )
    selected_package = bind_discovered_loss_package(
        selected, package=staged, loss_name="native_custom"
    )
    package = selected_package if packaged else None
    metadata = admission.objective_metadata(
        ObjectiveMetadataRequest(
            source=source, loss_name="native_custom", code_package=package
        )
    )
    assert metadata.source_sha256 == hashlib.sha256(source.encode()).hexdigest()
    assert metadata.effective_parameters == {"denominator": 2.0}
    material = ObjectiveReviewMaterial(
        sources=package.sources if package else {"native_custom.py": source},
        effective_parameters=metadata.effective_parameters,
        dependency_declaration="synthetic installed runtime",
    )
    numerical = NumericalReviewRequest(
        code_package=package,
        source=source,
        loss_name="native_custom",
        parameters=metadata.effective_parameters,
        prediction={
            "shape": [1, 2, 2],
            "dtype": "float32",
            "values": [0.0, 0.0, 0.0, 0.0],
        },
        target=(
            {"shape": [1, 2, 2], "dtype": "float32", "values": [0.0, 1.0, 0.0, 1.0]}
            if regressor
            else {"shape": [1, 2], "dtype": "int64", "values": [0, 1]}
        ),
    )

    class Gateway:
        def generate(self, *args, **kwargs):
            return {
                "decision": "approved",
                "reason": "synthetic fixture; not live review",
            }

    registry = p / "registry"
    registry.mkdir(mode=0o700)
    approved = review_native_objective_once(
        material,
        numerical,
        metadata,
        registry=registry,
        owner_uid=os.getuid(),
        run_id="synthetic",
        policy_sha256="a" * 64,
        allowed_import_roots=frozenset({"torch", "pydantic"}),
        numerical_worker=admission.numerical,
        gateway=Gateway(),
        deadline=admission.deadline,
    )
    assert approved.receipt.decision == "approved"
    review = p / "review.json"
    review.write_text(approved.model_dump_json())
    return approved, review, losses, metadata


def _admission_runtime(private):
    if shutil.which("bwrap") is None:
        pytest.skip("bubblewrap required for admission probe integration")
    root = Path(__file__).resolve().parents[2]
    paths = [
        Path(p)
        for p in ("/usr", "/lib", "/lib64", "/etc/ld.so.cache")
        if Path(p).exists()
    ]
    paths += [Path(sys.base_prefix).parent, root / ".venv", root / "experiments"]
    return AdmissionProbeRuntime(
        python=Path(sys.executable),
        namespace=ValidationNamespace(
            bubblewrap=Path(shutil.which("bwrap")),
            cwd=root,
            mounts=tuple(NamespaceMount(source=p, target=p) for p in paths),
        ),
        environment={"PATH": os.defpath, "OMP_NUM_THREADS": "1"},
        diagnostics=private,
        deadline=time.monotonic() + 40,
    )


def test_admission_probe_keeps_private_paths_hidden_and_does_not_reset_deadline(
    tmp_path,
):
    from dataclasses import replace

    secret = tmp_path / "private-answer.txt"
    secret.write_text("synthetic fixture only")
    runtime = _admission_runtime(tmp_path)
    source = f"""from pathlib import Path
assert not Path({str(secret)!r}).exists(), "private path visible"
from pydantic import BaseModel
class Config(BaseModel):
    scale: float = 2.0
class Loss:
    pass
PLUGIN_LOSS_TYPE="probe"
PLUGIN_LOSS_CONFIG_CLASS=Config
PLUGIN_LOSS_CLASS=Loss
PLUGIN_LOSS_TARGET_DTYPE="float"
"""
    result = runtime.objective_metadata(
        ObjectiveMetadataRequest(source=source, loss_name="probe")
    )
    assert result.effective_parameters == {"scale": 2.0}
    deadline = time.monotonic() + 3
    runtime = replace(runtime, deadline=deadline)
    request = ObjectiveMetadataRequest(
        source="import time\ntime.sleep(30)\n" + source, loss_name="probe"
    )
    with pytest.raises(TimeoutError, match="exceeded deadline"):
        runtime.objective_metadata(request)
    evidence = [json.loads(p.read_text()) for p in tmp_path.glob("*/timing.json")]
    assert sorted(item["status"] for item in evidence) == [
        "completed",
        "deadline_exhausted",
    ]
    assert time.monotonic() - deadline < 3
    directories = set(tmp_path.iterdir())
    with pytest.raises(TimeoutError, match="before probe"):
        runtime.objective_metadata(request)
    assert set(tmp_path.iterdir()) == directories


def test_model_discovery_uses_native_declaration_for_reexported_class(tmp_path):
    from dataclasses import replace

    from experiments.shared.native_model_discovery import ModelDiscoveryRequest

    plugins = tmp_path / "plugins"
    plugins.mkdir()
    declaration = plugins / "selected.py"
    source = 'from ml_models.models_sandbox import AE\nfrom ml_models.models_format_sandbox import AEConfig\nPLUGIN_MODEL_TYPE="exported_fixture"\nPLUGIN_MODEL_CLASS=AE\nPLUGIN_CONFIG_CLASS=AEConfig\nPLUGIN_OUTPUT_TYPE="classifier"\n'
    declaration.write_text(source)
    runtime = _admission_runtime(tmp_path)
    runtime = replace(
        runtime,
        namespace=runtime.namespace.model_copy(
            update={
                "mounts": (
                    *runtime.namespace.mounts,
                    NamespaceMount(source=plugins, target=plugins),
                ),
            }
        ),
        environment={**runtime.environment, "SIDERIUS_PLUGIN_DIRS": str(plugins)},
    )
    builtin = runtime.model_selection(ModelDiscoveryRequest(model_type="fcnet"))
    selected = runtime.model_selection(
        ModelDiscoveryRequest(model_type="exported_fixture")
    )
    assert builtin.plugin_path is None
    assert selected.plugin_path == declaration
    assert selected.source_sha256 == hashlib.sha256(source.encode()).hexdigest()
    assert selected.constructor_sha256 == builtin.constructor_sha256
    assert selected.source_sha256 != builtin.source_sha256
