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
    TaskOpaqueScopeRef,
)
from agent.schemas.data_analysis.common import canonical_sha256
from agent.schemas.data_analysis.resources import SamplingPolicy
from execute_tools.analysis_materialization import (
    AnalysisMaterializationRequest,
    AuthorizedAnalysisMaterializationRequest,
)
from tasks.tidmad.runtime import tidmad_data_path as tidmad_data_path_module
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope, TidmadTaskDataPath

from execute_tools.data_paths import bind_physical_data_root
from execute_tools.dataset_config import DataScope, bind_dataset_profile, tidmad_topology


def _authorized_request(
    *,
    profile,
    window_samples: int,
    information_class: str = "data",
    file_indices: list[int] | None = None,
    sampling_policy: SamplingPolicy | None = None,
):
    scope = LegacyPartitionScope(data_scope=DataScope(file_indices=file_indices or [0]))
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
        sampling_policy=sampling_policy
        or SamplingPolicy(mode="fixed", strategy="uniform", max_items=2, seed=17),
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


def _with_requested_format(authorized, format_id: str):
    request = authorized.request.model_copy(update={"requested_format_id": format_id})
    receipt = authorized.authorization_receipt.model_copy(
        update={"request_digest": canonical_sha256(request)}
    )
    return AuthorizedAnalysisMaterializationRequest(
        request=request, authorization_receipt=receipt
    )


def _write_validation_file(root, *, profile, samples: int, file_index: int = 0) -> np.ndarray:
    topology = tidmad_topology(profile)
    values = np.arange(samples, dtype=np.int16) % 255 - 128
    path = root / topology.dataset.validation_file_name(file_index)
    with h5py.File(path, "w") as handle:
        group = handle.create_group("timeseries")
        group.create_group(topology.channels.input_channel).create_dataset(
            "timeseries", data=values.astype(np.int8)
        )
        group.create_group(topology.channels.target_channel).create_dataset(
            "timeseries", data=np.zeros(samples, dtype=np.int8)
        )
    return values


def _model_segment_profile(profile, *, psd_segment_length: int):
    topology = dict(profile.topology)
    dataset = dict(topology["dataset"])
    dataset["psd_segment_length"] = psd_segment_length
    dataset["segments_per_file"] = 1
    topology["dataset"] = dataset
    return profile.model_copy(update={"topology": topology})


def _authorized_model_segment_request(
    *, profile, capability: TidmadTaskDataPath, information_class: str
):
    scope = TidmadScope(sample_set={0: [0]}, seg_size=4, profile=profile)
    serialized_scope = capability.serialize_scope(scope)
    scope_ref = TaskOpaqueScopeRef(
        task_data_path_id="tidmad",
        serialized_scope=serialized_scope,
        sha256=hashlib.sha256(serialized_scope.encode("utf-8")).hexdigest(),
    )
    role = (
        "validation_model_input_segments"
        if information_class == "data"
        else "validation_model_target_segments"
    )
    asset = AnalysisAsset(
        asset_id=f"tidmad-validation-{information_class}",
        asset_type="dataset",
        description="Exact candidate-sized TIDMAD validation rows.",
        location=TaskDataAssetLocation(
            task_data_path_id="tidmad",
            dataset_profile_sha256=hashlib.sha256(
                profile.model_dump_json().encode("utf-8")
            ).hexdigest(),
            logical_role=role,
        ),
        provenance=AssetProvenance(producer="tidmad-task-package"),
        authorized_scope=scope_ref,
        split_id="validation",
    )
    policy = AnalysisAccessPolicy(
        policy_id="tidmad-model-segment-test",
        policy_version=1,
        purpose="Verify exact target-isolated model input materialization.",
        split_rules=(
            {
                "split_id": "validation",
                "data_visible": True,
                "targets_visible": information_class == "target",
            },
        ),
    )
    request = AnalysisMaterializationRequest(
        request_id=f"request-{information_class}",
        invocation_id="invocation-model-segments",
        binding_id=f"binding-{information_class}",
        slot_id=information_class,
        asset=asset,
        split_id="validation",
        requested_scope=scope_ref,
        requested_information=(RequestedInformation(information_class=information_class),),
        requested_format_id="siderius.numeric-array.v1",
        operation="materialize",
        sampling_policy=SamplingPolicy(
            mode="fixed", strategy="uniform", max_items=2, seed=17
        ),
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
    return AuthorizedAnalysisMaterializationRequest(
        request=request, authorization_receipt=receipt
    )


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


def test_task_adapter_stratifies_across_every_requested_band_file(tmp_path, tidmad_profile) -> None:
    """Fails if a band-scoped selection silently omits one requested file."""

    window_samples = 16
    file_indices = [15, 16, 17, 18, 19]
    sources = {
        file_index: _write_validation_file(
            tmp_path,
            profile=tidmad_profile,
            samples=3 * window_samples,
            file_index=file_index,
        )
        for file_index in file_indices
    }
    capability = TidmadTaskDataPath()
    authorized = _authorized_request(
        profile=tidmad_profile,
        window_samples=window_samples,
        file_indices=file_indices,
        sampling_policy=SamplingPolicy(
            mode="fixed",
            strategy="task_defined",
            max_items=10,
            seed=17,
        ),
    )

    with bind_dataset_profile(tidmad_profile), bind_physical_data_root(str(tmp_path)):
        view = capability.materialize_analysis_view(authorized)

    exported = tmp_path / "materialized-band.npz"
    capability.export_analysis_materialization(view.content_ref, exported)
    with np.load(exported, allow_pickle=False) as payload:
        ids = payload["example_ids"].tolist()
        observed_files = [int(item.split("-")[1]) for item in ids]
        assert {file_index: observed_files.count(file_index) for file_index in file_indices} == {
            file_index: 2 for file_index in file_indices
        }
        for row, item in zip(payload["information__data"][:, 0], ids, strict=True):
            _, file_text, _, window_text = item.split("-")
            file_index = int(file_text)
            window_index = int(window_text)
            expected = (
                sources[file_index][
                    window_index * window_samples : (window_index + 1) * window_samples
                ]
                + 128
            )
            np.testing.assert_array_equal(row, expected)

    assert view.total_available == 15
    assert view.materialized_count == 10
    assert view.selection_identity.selected_count == 10


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


def test_window_asset_numeric_format_does_not_become_model_segment_scope(
    tmp_path, tidmad_profile
) -> None:
    """Fails if representation choice overrides the asset's scientific role."""

    window_samples = 32
    _write_validation_file(tmp_path, profile=tidmad_profile, samples=3 * window_samples)
    capability = TidmadTaskDataPath()
    authorized = _with_requested_format(
        _authorized_request(profile=tidmad_profile, window_samples=window_samples),
        "siderius.numeric-array.v1",
    )

    with bind_dataset_profile(tidmad_profile), bind_physical_data_root(str(tmp_path)):
        view = capability.materialize_analysis_view(authorized)

    exported = tmp_path / "window-numeric.npz"
    capability.export_analysis_materialization(view.content_ref, exported)
    with np.load(exported, allow_pickle=False) as payload:
        assert set(payload.files) == {"example_ids", "information__data"}
        assert payload["information__data"].shape == (2, window_samples)
    assert view.format_id == "siderius.numeric-array.v1"
    assert view.population_unit == "fixed-duration validation windows"


def test_model_input_segments_match_ordinary_row_geometry_without_target_read(
    tmp_path, tidmad_profile, monkeypatch
) -> None:
    """Fails if historical input rows drift or inference input opens target bytes."""

    profile = _model_segment_profile(tidmad_profile, psd_segment_length=16)
    source = _write_validation_file(tmp_path, profile=profile, samples=16)
    capability = TidmadTaskDataPath()
    authorized = _authorized_model_segment_request(
        profile=profile, capability=capability, information_class="data"
    )
    opened_channels: list[str] = []
    original = tidmad_data_path_module._h5_dataset

    def recording_h5_dataset(handle, *path):
        opened_channels.append(path[1])
        return original(handle, *path)

    monkeypatch.setattr(
        "tasks.tidmad.runtime.tidmad_data_path._h5_dataset", recording_h5_dataset
    )
    with bind_dataset_profile(profile), bind_physical_data_root(str(tmp_path)):
        view = capability.materialize_analysis_view(authorized)

    exported = tmp_path / "model-input.npz"
    capability.export_analysis_materialization(view.content_ref, exported)
    with np.load(exported, allow_pickle=False) as payload:
        assert set(payload.files) == {"example_ids", "information__data"}
        rows = payload["information__data"]
        selected = [int(item.rsplit("-", 1)[1]) for item in payload["example_ids"]]
        for row, row_index in zip(rows, selected, strict=True):
            expected = source[row_index * 4 : (row_index + 1) * 4] + 128
            np.testing.assert_array_equal(row, expected)

    topology = tidmad_topology(profile)
    assert opened_channels == [topology.channels.input_channel] * 2
    assert view.population_unit == "validation model-input segments"
    assert view.total_available == 4
    assert view.materialized_count == 2
