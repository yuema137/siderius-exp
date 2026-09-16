"""Ordinary and historical inference must agree before TIDMAD output encoding."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import h5py
import numpy as np
import torch
from agent.schemas.data_analysis.access import AnalysisAccessPolicy, RequestedInformation
from agent.schemas.data_analysis.assets import (
    AnalysisAsset,
    AnalysisAuthorizationReceipt,
    AssetProvenance,
    LegacyPartitionScope,
    TaskDataAssetLocation,
)
from agent.schemas.data_analysis.common import canonical_sha256
from agent.schemas.data_analysis.inference import (
    HistoricalInferenceConfiguration,
    HistoricalModelInferenceRequest,
)
from agent.schemas.data_analysis.resources import AnalysisResourceEnvelope, SamplingPolicy
from agent.schemas.data_analysis.trained_model import TrainedModelArtifact
from execute_tools.analysis_materialization import (
    AnalysisMaterializationRequest,
    AuthorizedAnalysisMaterializationRequest,
    HistoricalInferenceInputDerivationRequest,
    validate_derived_historical_inference_input_asset,
)
from execute_tools.historical_model_inference import (
    HistoricalInferenceInputPath,
    HistoricalInferenceRuntimeInputs,
    LocalPytorchHistoricalModelInferenceCapability,
)
from execute_tools.trained_model_artifact import (
    TrainedModelEmissionContext,
    TrainingArtifactCandidate,
    copy_certified_artifact,
    emit_trained_model_artifact,
)
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope, TidmadTaskDataPath

from execute_tools.data_paths import bind_physical_data_root
from execute_tools.dataset_config import DataScope, bind_dataset_profile, tidmad_topology
from execute_tools.generic_inference import run_generic_inference
from execute_tools.task_data_path import DeliverableWriteRequest, content_identity
from ml_models.models_format_sandbox import get_config_class
from ml_models.models_sandbox import construct_registered_model
from ml_models.plugin_loader import register_model_in_memory
from workflows.task_composition import compose_run_task_bindings

TASK_ROOT = Path(__file__).resolve().parents[3] / "tasks/tidmad"
MANIFEST = TASK_ROOT / "compositions/continuous_regression.yaml"
MODEL_PLUGIN = Path(__file__).resolve().parent / "fixtures/tiny_waveform_model.py"


class _CertifiedWorkspaceExporter:
    def __init__(self, root: Path) -> None:
        self.root = root

    def export_artifact(self, ref, destination: Path) -> None:
        copy_certified_artifact(self.root, ref, destination)


class _ExactModelPluginResolver:
    def resolve_model_plugin(self, identity) -> Path:
        assert identity.content_sha256 == hashlib.sha256(MODEL_PLUGIN.read_bytes()).hexdigest()
        return MODEL_PLUGIN


def test_same_checkpoint_and_selection_give_equivalent_scientific_predictions(
    tmp_path: Path, tidmad_profile, monkeypatch
) -> None:
    """The historical worker must reproduce ordinary pre-deliverable forward values."""

    topology = dict(tidmad_profile.topology)
    dataset = dict(topology["dataset"])
    dataset["psd_segment_length"] = 8
    dataset["segments_per_file"] = 1
    topology["dataset"] = dataset
    profile = tidmad_profile.model_copy(update={"topology": topology})
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    source = data_dir / tidmad_topology(profile).dataset.validation_file_name(0)
    with h5py.File(source, "w") as handle:
        group = handle.create_group("timeseries")
        group.create_group("channel0001").create_dataset(
            "timeseries", data=np.asarray([-4, -3, -2, -1, 0, 1, 2, 3], dtype=np.int8)
        )
        group.create_group("channel0002").create_dataset(
            "timeseries", data=np.zeros(8, dtype=np.int8)
        )

    register_model_in_memory(str(MODEL_PLUGIN))
    config_payload = {"model_type": "tidmad_tiny_waveform", "segmentation_size": 4}
    config_class = get_config_class("tidmad_tiny_waveform")
    assert config_class is not None
    model = construct_registered_model(
        "tidmad_tiny_waveform", config_class.model_validate(config_payload), loss_type="smooth_l1"
    )
    model.eval()
    checkpoint_path = tmp_path / "checkpoint.pt"
    torch.save(model.state_dict(), checkpoint_path)
    config_path = tmp_path / "model.json"
    config_path.write_text(json.dumps(config_payload), encoding="utf-8")
    task = TidmadTaskDataPath()
    scope = TidmadScope(sample_set={0: [0]}, seg_size=4, profile=profile)
    scope_path = tmp_path / "training_scope.json"
    scope_path.write_text(task.serialize_scope(scope), encoding="utf-8")

    composition = compose_run_task_bindings(str(MANIFEST))
    model_io = composition.forward_contract.model_io
    assert model_io is not None and model_io.inference is not None
    candidate = TrainingArtifactCandidate(
        checkpoint_path=str(checkpoint_path),
        checkpoint_sha256=hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        checkpoint_byte_size=checkpoint_path.stat().st_size,
        model_config_path=str(config_path),
        model_config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
        model_config_byte_size=config_path.stat().st_size,
        model_plugin_path=str(MODEL_PLUGIN),
        model_plugin_sha256=hashlib.sha256(MODEL_PLUGIN.read_bytes()).hexdigest(),
        model_plugin_member=MODEL_PLUGIN.name,
        model_type="tidmad_tiny_waveform",
        effective_loss_type="smooth_l1",
        training_scope_path=str(scope_path),
        training_scope_sha256=hashlib.sha256(scope_path.read_bytes()).hexdigest(),
    )
    artifact_root = tmp_path / "trained-artifacts"
    artifact_ref = emit_trained_model_artifact(
        candidate,
        TrainedModelEmissionContext(
            workspace=str(artifact_root),
            run_name="synthetic-parity",
            iteration_id="test-iteration",
            experiment_id="test-candidate",
            model_io_contract=model_io,
            forward_contract=composition.forward_contract,
            dataset_profile=profile.to_wire(),
            task_data_path_id="tidmad",
            task_data_path_content_sha256=hashlib.sha256(
                content_identity(task).encode("utf-8")
            ).hexdigest(),
            task_composition_fingerprint=canonical_sha256(
                {"test_task": "tidmad", "profile": profile.to_wire()}
            ),
            plugin_configured_ref="approved-test-plugin",
        ),
    )
    artifact = TrainedModelArtifact.model_validate_json(
        (artifact_root / artifact_ref.artifact_ref.logical_ref).read_bytes()
    )

    profile_json = profile.model_dump_json()
    base = AnalysisAsset(
        asset_id="declared-validation-file",
        asset_type="dataset",
        description="One declared synthetic TIDMAD validation file.",
        location=TaskDataAssetLocation(
            task_data_path_id="tidmad",
            dataset_profile_sha256=hashlib.sha256(profile_json.encode("utf-8")).hexdigest(),
            logical_role="validation_input_windows",
        ),
        provenance=AssetProvenance(producer="test-task"),
        authorized_scope=LegacyPartitionScope(data_scope=DataScope(file_indices=[0])),
        split_id="validation",
    )
    derivation = HistoricalInferenceInputDerivationRequest(
        base_asset=base,
        model_artifact=artifact,
        model_config_json=config_path.read_text(encoding="utf-8"),
        dataset_profile_json=profile_json,
    )
    derived = validate_derived_historical_inference_input_asset(
        derivation, task.derive_historical_inference_input_asset(derivation)
    )
    policy = AnalysisAccessPolicy(
        policy_id="synthetic-tidmad-parity",
        policy_version=1,
        purpose="Compare exact prediction semantics without target exposure.",
        split_rules=({"split_id": "validation", "data_visible": True},),
    )
    materialization_request = AnalysisMaterializationRequest(
        request_id="parity-input",
        invocation_id="parity-inference",
        binding_id="model-input",
        slot_id="features",
        asset=derived,
        split_id="validation",
        requested_scope=derived.authorized_scope,
        requested_information=(RequestedInformation(information_class="data"),),
        requested_format_id="siderius.numeric-array.v1",
        operation="materialize",
        sampling_policy=SamplingPolicy(mode="fixed", strategy="task_defined", max_items=2, seed=17),
        access_policy=policy,
    )
    authorization = AnalysisAuthorizationReceipt(
        invocation_id="parity-inference",
        binding_id="model-input",
        slot_id="features",
        request_digest=canonical_sha256(materialization_request),
        policy_digest=canonical_sha256(policy),
        asset_digest=canonical_sha256(derived),
        authorized_at="2026-09-16T00:00:00+00:00",
    )
    with bind_dataset_profile(profile), bind_physical_data_root(str(data_dir)):
        input_view = task.materialize_analysis_view(
            AuthorizedAnalysisMaterializationRequest(
                request=materialization_request, authorization_receipt=authorization
            )
        )
    input_path = tmp_path / "historical-input.npz"
    task.export_analysis_materialization(input_view.content_ref, input_path)
    with np.load(input_path, allow_pickle=False) as payload:
        assert payload["information__data"].dtype == np.dtype("int64")
        assert "information__target" not in payload.files

    ordinary_predictions: list[np.ndarray] = []
    original_writer = task.write_deliverable

    def capture_ordinary_predictions(predictions, write_request):
        def captured_stream():
            for prediction in predictions:
                ordinary_predictions.append(prediction.detach().cpu().numpy().copy())
                yield prediction

        return original_writer(captured_stream(), write_request)

    monkeypatch.setattr(task, "write_deliverable", capture_ordinary_predictions)
    with bind_dataset_profile(profile), bind_physical_data_root(str(data_dir)):
        ordinary = run_generic_inference(
            data_path=task,
            task_scope=scope,
            model=model,
            device=torch.device("cpu"),
            data_dir=str(data_dir),
            batch_size=2,
            input_dtype=torch.int64,
            write_request=DeliverableWriteRequest(
                output_dir=str(tmp_path / "ordinary-output"),
                exp_id="parity",
                run_name="synthetic-parity",
                model_type="tidmad_tiny_waveform",
            ),
        )
    assert ordinary.samples == 2
    assert len(ordinary_predictions) == 2

    model_authorization = AnalysisAuthorizationReceipt(
        invocation_id="parity-inference",
        binding_id="prediction-output",
        slot_id="predictions",
        request_digest="1" * 64,
        policy_digest=canonical_sha256(policy),
        asset_digest="2" * 64,
        authorized_at="2026-09-16T00:00:00+00:00",
    )
    inference_request = HistoricalModelInferenceRequest(
        request_id="parity-request",
        invocation_id="parity-inference",
        output_binding_id="prediction-output",
        output_slot_id="predictions",
        output_asset_id="test-trained-model",
        model_artifact=artifact,
        model_artifact_ref=artifact_ref,
        model_authorization_receipt=model_authorization,
        input_views=(input_view,),
        split_id="validation",
        requested_scope=derived.authorized_scope,
        selection_identity=input_view.selection_identity,
        requested_prediction_format="siderius.numeric-array.v1",
        requested_information=(RequestedInformation(information_class="prediction"),),
        configuration=HistoricalInferenceConfiguration(batch_size=2, device="cpu"),
        resource_envelope=AnalysisResourceEnvelope(
            wall_time_budget_s=30, per_skill_timeout_s=30, preferred_device="cpu"
        ),
        deadline_monotonic_s=time.monotonic() + 30,
    )
    capability = LocalPytorchHistoricalModelInferenceCapability(
        workspace=tmp_path / "historical-workspace",
        artifact_exporter=_CertifiedWorkspaceExporter(artifact_root),
        plugin_resolver=_ExactModelPluginResolver(),
    )
    outcome = capability.run_historical_inference(
        inference_request,
        HistoricalInferenceRuntimeInputs(
            paths=(
                HistoricalInferenceInputPath(
                    binding_id=input_view.binding_id, path=str(input_path)
                ),
            )
        ),
    )
    assert outcome.receipt.status == "completed", outcome.receipt.failure_message
    assert outcome.receipt.target_exposed_to_inference is False
    assert outcome.receipt.prediction_count == ordinary.samples
    assert outcome.view is not None
    prediction_path = tmp_path / "historical-predictions.npz"
    capability.export_historical_prediction(outcome.view.content_ref, prediction_path)
    with np.load(prediction_path, allow_pickle=False) as payload:
        np.testing.assert_allclose(
            payload["information__prediction"],
            np.stack(ordinary_predictions),
            rtol=1e-7,
            atol=0,
        )
        with np.load(input_path, allow_pickle=False) as model_input:
            np.testing.assert_array_equal(payload["example_ids"], model_input["example_ids"])
