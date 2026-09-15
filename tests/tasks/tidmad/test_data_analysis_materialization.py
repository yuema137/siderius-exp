"""Real-task adapter tests for the generic Data Analysis materialization ABI."""

from __future__ import annotations

import hashlib

import h5py
import numpy as np
import pytest
from agent.schemas.data_analysis.access import AnalysisAccessPolicy, RequestedInformation
from agent.schemas.data_analysis.assets import (
    AnalysisAsset,
    AnalysisAuthorizationReceipt,
    AssetProvenance,
    LegacyPartitionScope,
    TaskDataAssetLocation,
)
from agent.schemas.data_analysis.common import canonical_sha256
from agent.schemas.data_analysis.resources import SamplingPolicy
from execute_tools.analysis_materialization import (
    AnalysisMaterializationRequest,
    AuthorizedAnalysisMaterializationRequest,
)
from tasks.tidmad.runtime.tidmad_data_path import TidmadTaskDataPath

from execute_tools.data_paths import bind_physical_data_root
from execute_tools.dataset_config import DataScope, bind_dataset_profile, tidmad_topology


def _authorized_request(*, profile, window_samples: int, information_class: str = "data"):
    scope = LegacyPartitionScope(data_scope=DataScope(file_indices=[0]))
    asset = AnalysisAsset(
        asset_id="tidmad-validation-input",
        asset_type="dataset",
        description="Bounded TIDMAD validation input windows.",
        location=TaskDataAssetLocation(
            task_data_path_id="tidmad",
            dataset_profile_sha256=hashlib.sha256(
                profile.model_dump_json().encode("utf-8")
            ).hexdigest(),
            logical_role="validation_input_windows",
        ),
        provenance=AssetProvenance(producer="tidmad-task-package"),
        authorized_scope=scope,
        split_id="validation",
        metadata={"window_samples": window_samples},
        metadata_sources={
            "window_samples": {"information_class": "identity"},
        },
    )
    policy = AnalysisAccessPolicy(
        policy_id="tidmad-analysis-test",
        policy_version=1,
        purpose="Verify the task-owned materialization boundary.",
        split_rules=({"split_id": "validation", "data_visible": True},),
    )
    request = AnalysisMaterializationRequest(
        request_id="request-1",
        invocation_id="invocation-1",
        binding_id="binding-1",
        slot_id="series",
        asset=asset,
        split_id="validation",
        requested_scope=scope,
        requested_information=(RequestedInformation(information_class=information_class),),
        requested_format_id="siderius.timeseries-array.v1",
        operation="materialize",
        sampling_policy=SamplingPolicy(mode="fixed", strategy="uniform", max_items=2, seed=17),
        access_policy=policy,
    )
    receipt = AnalysisAuthorizationReceipt(
        invocation_id=request.invocation_id,
        binding_id=request.binding_id,
        slot_id=request.slot_id,
        request_digest=canonical_sha256(request),
        policy_digest=canonical_sha256(policy),
        asset_digest=canonical_sha256(asset),
        authorized_at="2026-09-15T00:00:00+00:00",
    )
    return AuthorizedAnalysisMaterializationRequest(request=request, authorization_receipt=receipt)


def _write_validation_file(root, *, profile, samples: int) -> np.ndarray:
    topology = tidmad_topology(profile)
    values = np.arange(samples, dtype=np.int16) % 255 - 128
    path = root / topology.dataset.validation_file_name(0)
    with h5py.File(path, "w") as handle:
        group = handle.create_group("timeseries")
        group.create_group(topology.channels.input_channel).create_dataset(
            "timeseries", data=values.astype(np.int8)
        )
        group.create_group(topology.channels.target_channel).create_dataset(
            "timeseries", data=np.zeros(samples, dtype=np.int8)
        )
    return values


def test_task_adapter_emits_bounded_regular_view_without_target(tmp_path, tidmad_profile) -> None:
    """Fails if task bytes, cadence, selection, or information isolation drift."""

    window_samples = 32
    source = _write_validation_file(tmp_path, profile=tidmad_profile, samples=3 * window_samples)
    capability = TidmadTaskDataPath()
    authorized = _authorized_request(profile=tidmad_profile, window_samples=window_samples)

    with bind_dataset_profile(tidmad_profile), bind_physical_data_root(str(tmp_path)):
        view = capability.materialize_analysis_view(authorized)

    exported = tmp_path / "materialized.npz"
    capability.export_analysis_materialization(view.content_ref, exported)
    with np.load(exported, allow_pickle=False) as payload:
        assert set(payload.files) == {
            "example_ids",
            "channel_ids",
            "valid_mask",
            "time_start_seconds",
            "time_step_seconds",
            "information__data",
        }
        assert payload["information__data"].shape == (2, 1, window_samples)
        assert "information__target" not in payload.files
        assert np.all(payload["time_step_seconds"] == 1e-7)
        assert np.all(payload["valid_mask"])
        selected = [int(item.rsplit("-", 1)[1]) for item in payload["example_ids"].tolist()]
        for row, index in zip(payload["information__data"][:, 0], selected, strict=True):
            expected = source[index * window_samples : (index + 1) * window_samples] + 128
            np.testing.assert_array_equal(row, expected)

    assert view.format_id == "siderius.timeseries-array.v1"
    assert view.materialized_count == 2
    assert view.total_available == 3
    assert view.selection_identity.selected_count == 2
    assert view.certified_information == (RequestedInformation(information_class="data"),)


def test_task_adapter_does_not_treat_requested_information_as_authority(
    tmp_path, tidmad_profile
) -> None:
    """Fails if an input-role asset can expose target merely because it was requested."""

    _write_validation_file(tmp_path, profile=tidmad_profile, samples=64)
    authorized = _authorized_request(
        profile=tidmad_profile,
        window_samples=32,
        information_class="target",
    )
    with (
        bind_dataset_profile(tidmad_profile),
        bind_physical_data_root(str(tmp_path)),
        pytest.raises(ValueError, match="does not match TIDMAD asset role"),
    ):
        TidmadTaskDataPath().materialize_analysis_view(authorized)
