"""TIDMAD's TaskDataPath implementation (D14-1 C2b).

OWNERSHIP. This module owns TIDMAD's executable data path: how training and
validation samples materialize from the HDF5 archives, and how model outputs
become the persisted ABRA deliverable / are read back for evaluation.
``TIDMADEpochDataset`` was MOVED VERBATIM here from
``execute_tools/train_engine_sandbox.py`` (D14-1 C2b; the engine re-exports
it, so every pre-existing import keeps resolving). Behaviour is pinned by the
committed pre-relocation manifest
``tests/unit/execute_tools/goldens/d14_tidmad_parity_manifest.json`` —
expected values are READ from that artifact, never recomputed.

BOUNDARIES (parent Amendment 2). Codec only: no metric arithmetic, no
scoreability thresholds, no objective semantics. The output path terminates
at the Step-06 evaluation authority — ``write_deliverable`` delegates to the
deliverable-spec naming/storage authorities and ``create_abra_file`` (imports,
not copies); ``read_evaluation_payload`` resolves the persisted deliverables
for the Step-06 handle and nothing more.

REGISTRATION. Importing this task module has no registry side effect. The
composition loader instantiates and binds it from the task manifest.

NOTE: no ``from __future__ import annotations`` here — under lazy annotations
ruff (UP037) would force de-quoting an annotation INSIDE the verbatim-moved
class block, breaking the C2b byte-parity guarantee. Eager annotations keep
the moved block byte-identical.
"""

import gc
import hashlib
import io
import json
import os
import random
from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Literal, cast

import h5py
import numpy as np
import torch
from agent.schemas.data_analysis.assets import (
    AnalysisAsset,
    AssetProvenance,
    LegacyPartitionScope,
    MaterializedAnalysisView,
    TaskDataAssetLocation,
    TaskOpaqueScopeRef,
)
from agent.schemas.data_analysis.common import CertifiedArtifactRef, canonical_sha256
from agent.schemas.data_analysis.resources import CertifiedSelectionIdentity
from agent.schemas.data_analysis.view_formats import NUMERIC_ARRAY_V1, TIMESERIES_ARRAY_V1
from execute_tools.analysis_materialization import (
    AuthorizedAnalysisMaterializationRequest,
    HistoricalInferenceInputDerivationRequest,
)
from pydantic import BaseModel, ConfigDict, Field
from torch.utils.data import Dataset

from execute_tools.array2h5 import create_abra_file
from execute_tools.data_paths import resolve_physical_data_root
from execute_tools.dataset_config import (
    DataScope,
    DatasetProfile,
    resolve_dataset_profile,
    tidmad_topology,
)
from execute_tools.deliverable_spec import (
    DeliverableStorage,
    default_deliverable_storage,
    derive_tidmad_deliverable_spec,
)
from execute_tools.health_checks.config import load_composed_health_config
from execute_tools.sample_set_builder import build_sample_set
from execute_tools.task_data_path import (
    DeliverableWriteRequest,
    EpochSamplingParams,
    EvalMaterializationParams,
    EvaluationReadRequest,
    HealthCoverageRequest,
    HealthCoverageResult,
    ScopeBuildRequest,
    StorageReadScope,
    TaskEvaluationPayload,
    ValidationScopeError,
)

_TIDMAD_TASK_DATA_PATH_ID = "tidmad"


def _h5_dataset(f: h5py.File, *path: str) -> h5py.Dataset:
    """Type-only helper: walk an HDF5 path and narrow the final node to Dataset.

    Per-module copy, mirroring the identical shims in
    ``train_engine_sandbox.py``, ``inference_single.py`` and
    ``scoring_utils.py`` (the established per-module pattern — a shared import
    from the engine would recreate the cycle the C2b move exists to avoid).
    """
    node: Any = f
    for k in path:
        node = node[k]
    return cast(h5py.Dataset, node)


def _stratified_analysis_indices(
    available_by_file: dict[int, int], selected_count: int, rng: np.random.Generator
) -> dict[int, np.ndarray]:
    """The task-owned per-file coverage rule shared by both analysis layouts."""

    if not available_by_file or any(count <= 0 for count in available_by_file.values()):
        raise ValueError("every requested TIDMAD analysis file must contain available rows")
    if selected_count < len(available_by_file):
        raise ValueError(
            "stratified TIDMAD band sampling requires at least one item per requested file"
        )
    remaining = selected_count
    active = list(available_by_file)
    allocations = {index: 0 for index in available_by_file}
    while remaining and active:
        for file_index in tuple(active):
            if remaining == 0:
                break
            if allocations[file_index] >= available_by_file[file_index]:
                active.remove(file_index)
                continue
            allocations[file_index] += 1
            remaining -= 1
    return {
        file_index: np.sort(rng.choice(available, size=allocations[file_index], replace=False))
        for file_index, available in available_by_file.items()
    }


class TIDMADEpochDataset(Dataset):
    """
    Dataset that loads subsampled segments from multiple HDF5 files.

    Created and destroyed each epoch. Collects ``train_portion`` of each
    file's segments, loads them via HDF5 direct slicing, and concatenates
    into a single shuffleable dataset. Cross-file shuffling happens
    naturally via the DataLoader's ``shuffle=True``.

    Peak memory: ``train_portion * sum(segments_per_file) * seg_size`` bytes
    per channel. E.g. train_portion=0.1, 20 files × 10 segs = 200 PSD segs
    → 200 × 1000 × 10000 = 200 MB per channel.
    """

    def __init__(
        self,
        data_dir: str,
        sample_set: dict,
        seg_size: int,
        train_portion: float | None = None,
        rng: "random.Random | None" = None,
        profile: DatasetProfile | None = None,
        max_samples: int | None = None,
        file_family: Literal["training", "validation"] = "training",
    ):
        """
        Args:
            data_dir:       Directory containing ``abra_training_XXXX.h5``.
            sample_set:     ``{file_index: [segment_indices]}`` — the data scope.
            seg_size:       ML segmentation size (e.g. 10000).
            train_portion:  Fraction of each file's segments to use. When None
                            or 1.0, all segments in the scope are loaded.
            rng:            Random instance for reproducible subsampling.
            max_samples:    VALIDATION POSTURE ONLY. Absolute ceiling on the ML
                            segments this epoch may contain. ``None`` (every
                            production campaign) loads the full selection.
            file_family:    Which file family of the Dataset Profile the
                            indices address — ``"training"`` (default; the
                            pre-07a behaviour, byte-for-byte) or
                            ``"validation"`` (Step 07a: the R3 validation pass
                            reads the eval SampleSet from the VALIDATION
                            family through ``DatasetConfig.validation_file_name``).
                            The family is the ONLY thing that changes; the
                            geometry, subsampling and row layout are shared.

        **Why an absolute ceiling exists beside ``train_portion``.** A
        fraction cannot bound the epoch, because what it is a fraction OF
        is not harness-owned: ``ml_segs_per_psd`` is
        ``psd_segment_length // seg_size`` and ``seg_size`` comes from the
        planner's model config, so 1 % of the scope at ``seg_size=1000``
        is ten times the samples it is at ``seg_size=10000``. During
        Step 03 a 1 %-portion plan resolved to 12,500 optimizer steps.

        Enforced by reading LESS, not by stopping later: files stop being
        opened once the budget is met, and the concatenated arrays are cut
        to exactly ``max_samples``. Both the HDF5 reads and the optimizer
        steps shrink, so the epoch is small rather than merely truncated —
        the whole point of bounding before execution instead of killing
        during it.
        """
        if rng is None:
            rng = random.Random()

        # Regime-A when no profile is supplied (§5c).
        self.profile = profile or resolve_dataset_profile()
        dataset = tidmad_topology(self.profile).dataset
        channels = tidmad_topology(self.profile).channels
        enc = tidmad_topology(self.profile).encoding
        psd_len = dataset.psd_segment_length
        ml_segs_per_psd = psd_len // seg_size
        all_ch1, all_ch2 = [], []
        # Row span each file occupies in the concatenated arrays, recorded as
        # the rows are appended. Sequential ordering needs to address one
        # file's rows without re-deriving the layout — and re-deriving it
        # would be wrong anyway, since a missing file is skipped below and
        # contributes no rows at all.
        self.file_row_ranges: dict[int, tuple[int, int]] = {}
        rows_so_far = 0
        #: PSD segments actually READ from disk. The envelope's claim is
        #: that it avoids work rather than discarding it, and the row
        #: count alone cannot show that — the post-hoc cut leaves the same
        #: length whether one PSD segment was read or a hundred were.
        self.psd_segments_read = 0

        for file_key in sorted(sample_set.keys(), key=int):
            if max_samples is not None and rows_so_far >= max_samples:
                break
            file_index = int(file_key)
            file_name = (
                dataset.training_file_name(file_index)
                if file_family == "training"
                else dataset.validation_file_name(file_index)
            )
            file_path = os.path.join(data_dir, file_name)
            if not os.path.exists(file_path):
                print(f"Warning: {file_path} not found, skipping.")
                continue

            scope_segments = sample_set[file_key]
            # Inline the subsample predicate so pyright narrows ``train_portion``
            # to ``float`` inside this branch (previous ``use_subsample`` helper
            # broke that narrowing). The else-leg preserves the original
            # "full-scope when train_portion is None or >= 1.0" semantics.
            if train_portion is not None and train_portion < 1.0:
                n_keep = max(1, round(train_portion * len(scope_segments)))
                segments = rng.sample(scope_segments, n_keep)
            else:
                segments = scope_segments

            if max_samples is not None:
                # Stop READING once the budget is met. Ceiling division, so
                # the last PSD needed to reach the cap is still read and the
                # exact cut happens on the concatenated rows below.
                needed = max_samples - rows_so_far
                segments = segments[: -(-needed // ml_segs_per_psd)]

            with h5py.File(file_path, "r") as f:
                ch1 = _h5_dataset(f, "timeseries", channels.input_channel, "timeseries")
                ch2 = _h5_dataset(
                    f, "timeseries", channels.target_channel, "timeseries"
                )
                for psd_idx in segments:
                    start = psd_idx * psd_len
                    end = start + psd_len
                    all_ch1.append(
                        np.array(ch1[start:end], dtype=enc.storage_dtype).reshape(
                            ml_segs_per_psd, seg_size
                        )
                    )
                    all_ch2.append(
                        np.array(ch2[start:end], dtype=enc.storage_dtype).reshape(
                            ml_segs_per_psd, seg_size
                        )
                    )

            self.psd_segments_read += len(segments)
            file_rows = len(segments) * ml_segs_per_psd
            if file_rows:
                self.file_row_ranges[file_index] = (
                    rows_so_far,
                    rows_so_far + file_rows,
                )
                rows_so_far += file_rows

            gc.collect()

        self.inputs = (
            np.concatenate(all_ch1, axis=0)
            if all_ch1
            else np.empty((0, seg_size), dtype=enc.storage_dtype)
        )
        self.targets = (
            np.concatenate(all_ch2, axis=0)
            if all_ch2
            else np.empty((0, seg_size), dtype=enc.storage_dtype)
        )

        if max_samples is not None and len(self.inputs) > max_samples:
            self.inputs = self.inputs[:max_samples]
            self.targets = self.targets[:max_samples]
            # Sequential ordering addresses rows through these ranges, so a
            # range extending past the cut would index rows that no longer
            # exist. Clip the straddling file and drop any that start beyond
            # the cut (a file loop can only ever leave one of each).
            self.file_row_ranges = {
                idx: (start, min(end, max_samples))
                for idx, (start, end) in self.file_row_ranges.items()
                if start < max_samples
            }

    def __len__(self):
        return len(self.inputs)

    def __getitem__(self, idx):
        enc = tidmad_topology(self.profile).encoding
        return (
            self.inputs[idx].astype(enc.compute_dtype) + enc.value_offset,
            self.targets[idx].astype(enc.compute_dtype) + enc.value_offset,
        )


@dataclass(frozen=True)
class _ValidationSegment:
    """One selected PSD segment in the validation dataset's logical row map."""

    file_path: str
    sample_start: int
    row_start: int
    row_end: int


class TIDMADValidationDataset(Dataset):
    """Exact validation view that reads selected HDF5 rows on demand.

    Construction validates file/channel presence, physical segment bounds and
    the complete logical row map, but does not read signal arrays. Individual
    ML rows are read when a DataLoader requests them, so peak resident data is
    governed by the loader batch rather than the complete Formal scope.

    HDF5 handles are cached per process. The PID check and ``__getstate__``
    ensure a future worker process never reuses its parent's open handles.

    This class remains in the task-data-path plugin module deliberately. File
    plugins are cold-loaded without adding the experiment repository to
    ``sys.path``; moving this implementation to an unpinned sibling import
    would make the real training/inference children unable to load the task.
    """

    def __init__(
        self,
        *,
        data_dir: str,
        sample_set: dict,
        seg_size: int,
        profile: DatasetProfile,
    ) -> None:
        self.profile = profile
        self.seg_size = seg_size
        topology = tidmad_topology(profile)
        self._dataset = topology.dataset
        self._channels = topology.channels
        self._encoding = topology.encoding
        self._ml_segs_per_psd = self._dataset.psd_segment_length // seg_size
        self.file_row_ranges: dict[int, tuple[int, int]] = {}
        self._segments: list[_ValidationSegment] = []
        self._segment_row_ends: list[int] = []
        self._handles: dict[str, h5py.File] = {}
        self._handle_pid = os.getpid()

        rows_so_far = 0
        for file_key in sorted(sample_set, key=int):
            file_index = int(file_key)
            file_path = os.path.join(
                data_dir, self._dataset.validation_file_name(file_index)
            )
            if not os.path.exists(file_path):
                continue

            selected = tuple(int(segment) for segment in sample_set[file_key])
            self._validate_segments(file_path, file_index, selected)
            file_start = rows_so_far
            for psd_index in selected:
                row_end = rows_so_far + self._ml_segs_per_psd
                self._segments.append(
                    _ValidationSegment(
                        file_path=file_path,
                        sample_start=psd_index * self._dataset.psd_segment_length,
                        row_start=rows_so_far,
                        row_end=row_end,
                    )
                )
                self._segment_row_ends.append(row_end)
                rows_so_far = row_end
            if rows_so_far > file_start:
                self.file_row_ranges[file_index] = (file_start, rows_so_far)

        self._row_count = rows_so_far

    def _validate_segments(
        self, file_path: str, file_index: int, selected: tuple[int, ...]
    ) -> None:
        with h5py.File(file_path, "r") as handle:
            input_data = _h5_dataset(
                handle, "timeseries", self._channels.input_channel, "timeseries"
            )
            target_data = _h5_dataset(
                handle, "timeseries", self._channels.target_channel, "timeseries"
            )
            available = (
                min(len(input_data), len(target_data))
                // self._dataset.psd_segment_length
            )
        invalid = [segment for segment in selected if not 0 <= segment < available]
        if invalid:
            raise ValidationScopeError(
                f"validation scope requests PSD segment(s) {invalid!r} of file "
                f"{file_index}, but {file_path!r} holds only {available} complete "
                "PSD segment(s)."
            )

    def __len__(self) -> int:
        return self._row_count

    def _reset_inherited_handles(self) -> None:
        current_pid = os.getpid()
        if current_pid != self._handle_pid:
            self.close()
            self._handle_pid = current_pid

    def _handle(self, path: str) -> h5py.File:
        self._reset_inherited_handles()
        handle = self._handles.get(path)
        if handle is None:
            handle = h5py.File(path, "r")
            self._handles[path] = handle
        return handle

    def _row_location(self, idx: int) -> tuple[_ValidationSegment, int, int]:
        if idx < 0:
            idx += self._row_count
        if idx < 0 or idx >= self._row_count:
            raise IndexError(idx)
        segment = self._segments[bisect_right(self._segment_row_ends, idx)]
        row_within_segment = idx - segment.row_start
        start = segment.sample_start + row_within_segment * self.seg_size
        return segment, start, start + self.seg_size

    def _storage_row(self, idx: int, channel: str) -> np.ndarray:
        segment, start, end = self._row_location(idx)
        dataset = _h5_dataset(
            self._handle(segment.file_path), "timeseries", channel, "timeseries"
        )
        return np.asarray(dataset[start:end], dtype=self._encoding.storage_dtype)

    def __getitem__(self, idx: int) -> tuple[np.ndarray, np.ndarray]:
        return (
            self._storage_row(idx, self._channels.input_channel).astype(
                self._encoding.compute_dtype
            )
            + self._encoding.value_offset,
            self._storage_row(idx, self._channels.target_channel).astype(
                self._encoding.compute_dtype
            )
            + self._encoding.value_offset,
        )

    def materialize_storage_targets(self, start: int, end: int) -> np.ndarray:
        """Read a bounded contiguous logical target range in storage encoding."""
        if start < 0 or end < start or end > self._row_count:
            raise IndexError((start, end))
        targets = np.empty(
            (end - start, self.seg_size), dtype=self._encoding.storage_dtype
        )
        logical_row = start
        output_row = 0
        while logical_row < end:
            segment = self._segments[bisect_right(self._segment_row_ends, logical_row)]
            rows = min(end, segment.row_end) - logical_row
            row_within_segment = logical_row - segment.row_start
            sample_start = segment.sample_start + row_within_segment * self.seg_size
            sample_end = sample_start + rows * self.seg_size
            target_data = _h5_dataset(
                self._handle(segment.file_path),
                "timeseries",
                self._channels.target_channel,
                "timeseries",
            )
            targets[output_row : output_row + rows] = np.asarray(
                target_data[sample_start:sample_end],
                dtype=self._encoding.storage_dtype,
            ).reshape(rows, self.seg_size)
            logical_row += rows
            output_row += rows
        return targets

    def close(self) -> None:
        handles = getattr(self, "_handles", {})
        for handle in handles.values():
            handle.close()
        handles.clear()

    def __getstate__(self) -> dict[str, Any]:
        self.close()
        state = self.__dict__.copy()
        state["_handles"] = {}
        return state

    def __del__(self) -> None:
        self.close()


def is_complete_trial_output(
    path: str, expected_samples: int, storage: DeliverableStorage | None = None
) -> bool:
    """Return whether an attempt-scoped trial HDF5 is safe to reuse.

    A CUDA/host failure can leave earlier files from the same inference
    subprocess fully flushed while later files are absent or incomplete.
    Reuse is deliberately opt-in and requires both channels to be readable
    vectors of the exact expected length in the persisted storage dtype.

    Step 05c — this is a READER of the deliverable and it restated both facts
    the producer writes: the two channel-group names and the storage dtype.
    Left inlined, a task whose profile named different channels would have had
    every output declared incomplete and silently re-inferred. ``storage``
    defaults to the shipped representation, so a caller predating 05c is
    unaffected.

    D14-1 C4: moved verbatim from ``inference_single`` (which re-exports it) —
    a deliverable READER belongs with the deliverable codec.
    """
    resolved = storage if storage is not None else default_deliverable_storage()
    try:
        with h5py.File(path, "r") as handle:
            channel1 = _h5_dataset(
                handle, "timeseries", resolved.input_channel_group, "timeseries"
            )
            channel2 = _h5_dataset(
                handle, "timeseries", resolved.target_channel_group, "timeseries"
            )
            expected_shape = (expected_samples,)
            expected_dtype = np.dtype(resolved.storage_dtype)
            if (
                channel1.shape != expected_shape
                or channel2.shape != expected_shape
                or channel1.dtype != expected_dtype
                or channel2.dtype != expected_dtype
            ):
                return False
            # Force reads at both allocation boundaries. Opening metadata alone
            # is insufficient evidence that the final chunks were flushed.
            if expected_samples:
                channel1[0]
                channel1[-1]
                channel2[0]
                channel2[-1]
        return True
    except (KeyError, OSError, ValueError):
        return False


#: The scope payload's self-identifying tag. A scope that does not declare it
#: is refused BEFORE any field is read — a wrong-task payload must fail by
#: name, not by whichever field happens to be missing first.
_TIDMAD_SCOPE_KIND = "tidmad_scope_v1"

#: TIDMAD's trial-anchoring artifact, relocated from the tuner at B7.
_TIDMAD_ANCHOR_MAP_NAME = "segment_anchors.json"


class TidmadScope(BaseModel):
    """TIDMAD's opaque ``scope`` (child §3: scope is task-owned vocabulary).

    Carries exactly what the two engine construction sites pass beyond the
    framework-level ``*Params`` knobs: the DataScope-validated sample set
    (``{file_index: [psd_segment_indices]}``), the planner's ML segmentation
    size, and the dataset-profile identity. ``profile=None`` preserves the
    class's own regime-A fallback (``resolve_dataset_profile()``).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    sample_set: dict
    seg_size: int = Field(ge=1)
    profile: DatasetProfile | None = None


class TidmadTaskDataPath:
    """The registered TIDMAD implementation of the four-method seam.

    ``training_dataset`` / ``validation_dataset`` construct the (moved)
    ``TIDMADEpochDataset`` exactly as the engine call sites do today —
    parity with the pre-relocation manifest is asserted per grid cell.
    ``write_deliverable`` / ``read_evaluation_payload`` delegate to the
    deliverable-spec authorities (naming + storage) and ``create_abra_file``.
    """

    task_data_path_id: ClassVar[str] = _TIDMAD_TASK_DATA_PATH_ID

    def derive_historical_inference_input_asset(
        self, request: HistoricalInferenceInputDerivationRequest
    ) -> AnalysisAsset:
        """Translate certified candidate geometry within the declared validation region.

        This pure task-owned step does not open data or choose a sample. The
        downstream materializer owns bounded row selection and retains target
        isolation; the model artifact owns the effective segmentation size.
        """

        base = request.base_asset
        if not isinstance(base.authorized_scope, LegacyPartitionScope):
            raise ValueError("TIDMAD historical inference requires a declared partition region")
        location = base.location
        if not isinstance(location, TaskDataAssetLocation) or (
            location.logical_role != "validation_input_windows"
        ):
            raise ValueError("TIDMAD historical inference base must be validation input data")
        profile = DatasetProfile.model_validate_json(request.dataset_profile_json)
        topology = tidmad_topology(profile)
        config = json.loads(request.model_config_json)
        seg_size = config.get("segmentation_size")
        if not isinstance(seg_size, int) or isinstance(seg_size, bool) or seg_size <= 0:
            raise ValueError("certified TIDMAD model config lacks a valid segmentation_size")
        if topology.dataset.psd_segment_length % seg_size:
            raise ValueError("candidate segmentation_size does not divide the PSD segment length")
        files = base.authorized_scope.data_scope.resolve(profile.partition_count)
        sample_set = {
            file_index: list(range(topology.dataset.segments_per_file)) for file_index in files
        }
        scope = TidmadScope(sample_set=sample_set, seg_size=seg_size, profile=profile)
        serialized = self.serialize_scope(scope)
        return AnalysisAsset(
            asset_id=f"tidmad-historical-input-{request.model_artifact.model_artifact_id}",
            asset_type="dataset",
            description="Candidate-compatible validation input segments in the declared region.",
            location=TaskDataAssetLocation(
                task_data_path_id=self.task_data_path_id,
                dataset_profile_sha256=location.dataset_profile_sha256,
                logical_role="validation_model_input_segments",
            ),
            provenance=AssetProvenance(
                producer="tidmad-task-owned-input-derivation",
                source_asset_ids=(base.asset_id,),
            ),
            authorized_scope=TaskOpaqueScopeRef(
                task_data_path_id=self.task_data_path_id,
                serialized_scope=serialized,
                sha256=hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            ),
            split_id=base.split_id,
            allowed_operations=("materialize",),
        )

    def _analysis_payload_store(self) -> dict[str, bytes]:
        store = getattr(self, "_analysis_payloads", None)
        if store is None:
            store = {}
            self._analysis_payloads = store
        return cast(dict[str, bytes], store)

    def materialize_analysis_view(
        self,
        authorized: AuthorizedAnalysisMaterializationRequest,
    ) -> MaterializedAnalysisView:
        """Materialize a bounded, row-aligned real TIDMAD time-series view.

        This task-owned adapter reads only the explicitly scoped validation
        partition and only the information class authorized by the request.
        It performs no interpolation, filtering, resampling, or repair.
        """

        request = authorized.request
        location = request.asset.location
        model_segment_roles = {
            "validation_model_input_segments",
            "validation_model_target_segments",
        }
        if (
            isinstance(location, TaskDataAssetLocation)
            and location.logical_role in model_segment_roles
        ):
            if request.requested_format_id != NUMERIC_ARRAY_V1:
                raise ValueError("TIDMAD model-segment assets require numeric-array.v1")
            return self._materialize_model_segment_view(authorized)
        if request.requested_format_id not in {NUMERIC_ARRAY_V1, TIMESERIES_ARRAY_V1}:
            raise ValueError(
                "TIDMAD analysis supports only numeric-array.v1 and "
                "timeseries-array.v1"
            )
        if not isinstance(request.requested_scope, LegacyPartitionScope):
            raise ValueError("TIDMAD analysis requires a legacy-partition scope")
        if not isinstance(location, TaskDataAssetLocation):
            raise ValueError("TIDMAD analysis requires a task-data asset")
        requested_classes = tuple(item.information_class for item in request.requested_information)
        role_to_information = {
            "validation_input_windows": ("data", "input_channel"),
            "validation_target_windows": ("target", "target_channel"),
            "validation_residual_windows": ("residual", "target_channel"),
        }
        expected = role_to_information.get(location.logical_role)
        if expected is None or requested_classes != (expected[0],):
            raise ValueError("requested information does not match TIDMAD asset role")
        if expected[0] == "residual":
            raise ValueError("residuals must be supplied as certified evaluation artifacts")

        # Analysis-window extent is caller/task-composition policy, not model
        # training geometry. Requiring the descriptor to state it keeps the
        # task adapter free of a validation-treatment default and leaves
        # ``segmentation_size`` under its existing training-plan authority.
        window_samples = request.asset.metadata.get("window_samples")
        if (
            not isinstance(window_samples, int)
            or isinstance(window_samples, bool)
            or window_samples <= 0
        ):
            raise ValueError(
                "TIDMAD analysis assets require a positive integer "
                "metadata.window_samples declaration"
            )

        profile = resolve_dataset_profile()
        topology = tidmad_topology(profile)
        file_indices = request.requested_scope.data_scope.file_indices
        if not file_indices:
            raise ValueError("TIDMAD analysis requires at least one file index")
        resolved_file_indices = tuple(int(index) for index in file_indices)
        if len(set(resolved_file_indices)) != len(resolved_file_indices):
            raise ValueError("TIDMAD analysis file indices must be unique")
        data_root = resolve_physical_data_root()
        channel_name = getattr(topology.channels, expected[1])
        available_by_file: dict[int, int] = {}
        for file_index in resolved_file_indices:
            source = Path(data_root) / topology.dataset.validation_file_name(file_index)
            with h5py.File(source, "r") as handle:
                values = _h5_dataset(handle, "timeseries", channel_name, "timeseries")
                available_by_file[file_index] = len(values) // window_samples
        if any(count <= 0 for count in available_by_file.values()):
            raise ValueError(
                "every requested TIDMAD analysis file must contain at least one "
                "complete declared analysis window"
            )

        total_available = sum(available_by_file.values())
        policy = request.sampling_policy
        selected_count = total_available
        if policy.fraction is not None:
            selected_count = max(1, round(total_available * policy.fraction))
        if policy.max_items is not None:
            selected_count = min(selected_count, policy.max_items)
        if (
            policy.mode == "representative"
            and policy.max_items is None
            and policy.fraction is None
        ):
            selected_count = min(max(4, len(resolved_file_indices)), total_available)

        rng = np.random.default_rng(policy.seed)
        selected_by_file: dict[int, np.ndarray]
        if policy.strategy in {"stratified", "task_defined"}:
            selected_by_file = _stratified_analysis_indices(available_by_file, selected_count, rng)
        else:
            population = [
                (file_index, window_index)
                for file_index in resolved_file_indices
                for window_index in range(available_by_file[file_index])
            ]
            if selected_count == total_available:
                chosen_positions = np.arange(total_available, dtype=np.int64)
            else:
                chosen_positions = np.sort(
                    rng.choice(total_available, size=selected_count, replace=False)
                )
            selected_lists: dict[int, list[int]] = {
                index: [] for index in resolved_file_indices
            }
            for position in chosen_positions:
                file_index, window_index = population[int(position)]
                selected_lists[file_index].append(window_index)
            selected_by_file = {
                index: np.asarray(indices, dtype=np.int64)
                for index, indices in selected_lists.items()
            }

        rows_list: list[np.ndarray] = []
        example_id_list: list[str] = []
        for file_index in resolved_file_indices:
            source = Path(data_root) / topology.dataset.validation_file_name(file_index)
            with h5py.File(source, "r") as handle:
                values = _h5_dataset(handle, "timeseries", channel_name, "timeseries")
                for index in selected_by_file[file_index]:
                    rows_list.append(
                        np.asarray(
                            values[
                                int(index) * window_samples : (int(index) + 1) * window_samples
                            ],
                            dtype=np.int16,
                        )
                        + topology.encoding.value_offset
                    )
                    example_id_list.append(
                        f"validation-{file_index:04d}-window-{int(index):06d}"
                    )
        rows = np.stack(rows_list)

        example_ids = np.asarray(example_id_list, dtype="U48")
        selection_sha = canonical_sha256({"example_ids": example_ids.tolist()})
        selection = CertifiedSelectionIdentity(
            selection_id=f"tidmad-validation-{selection_sha[:16]}",
            selection_sha256=selection_sha,
            sampling_policy_sha256=canonical_sha256(request.sampling_policy),
            sampling_mode=policy.mode,
            sampling_strategy=policy.strategy,
            sampling_seed=policy.seed,
            population_unit="fixed-duration validation windows",
            total_available=total_available,
            selected_count=len(example_ids),
        )
        buffer = io.BytesIO()
        if request.requested_format_id == TIMESERIES_ARRAY_V1:
            np.savez(
                buffer,
                example_ids=example_ids,
                channel_ids=np.asarray([channel_name], dtype="U32"),
                valid_mask=np.ones((len(example_ids), window_samples), dtype=np.bool_),
                time_start_seconds=np.zeros(len(example_ids), dtype=np.float64),
                time_step_seconds=np.full(
                    len(example_ids),
                    1.0 / topology.dataset.sampling_frequency,
                    dtype=np.float64,
                ),
                **{f"information__{expected[0]}": rows[:, np.newaxis, :]},
            )
        else:
            np.savez(
                buffer,
                example_ids=example_ids,
                **{f"information__{expected[0]}": rows},
            )
        payload = buffer.getvalue()
        digest = hashlib.sha256(payload).hexdigest()
        logical_ref = f"opaque://tidmad-analysis/{request.binding_id}/{digest}"
        self._analysis_payload_store()[logical_ref] = payload
        return MaterializedAnalysisView(
            materialization_id=f"tidmad-{request.binding_id}-{digest[:16]}",
            invocation_id=request.invocation_id,
            binding_id=request.binding_id,
            slot_id=request.slot_id,
            asset_id=request.asset.asset_id,
            split_id=request.split_id,
            content_ref=CertifiedArtifactRef(
                logical_ref=logical_ref,
                sha256=digest,
                media_type="application/x-npz",
                byte_size=len(payload),
            ),
            format_id=request.requested_format_id,
            population_unit="fixed-duration validation windows",
            total_available=total_available,
            materialized_count=len(example_ids),
            certified_information=request.requested_information,
            selection_identity=selection,
            task_data_path_id=self.task_data_path_id,
            source_digests=(digest,),
            authorization_receipt=authorized.authorization_receipt,
        )

    def _materialize_model_segment_view(
        self,
        authorized: AuthorizedAnalysisMaterializationRequest,
    ) -> MaterializedAnalysisView:
        """Expose exact candidate-sized validation rows without reading the other channel.

        Ordinary composed evaluation iterates :meth:`validation_dataset` in
        deterministic row order.  This materializer uses the same task scope,
        PSD geometry, value offset and row order, but reads only the one channel
        authorized by the asset.  In particular, an inference-input request
        never opens the target dataset.
        """

        request = authorized.request
        if not isinstance(request.requested_scope, TaskOpaqueScopeRef):
            raise ValueError("TIDMAD model-segment analysis requires a task-opaque scope")
        if request.requested_scope.task_data_path_id != self.task_data_path_id:
            raise ValueError("TIDMAD model-segment scope belongs to another task data path")
        location = request.asset.location
        if not isinstance(location, TaskDataAssetLocation):
            raise ValueError("TIDMAD model-segment analysis requires a task-data asset")
        role_to_channels = {
            "validation_model_input_segments": {
                "data": "input_channel",
                "target": "target_channel",
            },
            "validation_model_target_segments": {"target": "target_channel"},
        }
        channels = role_to_channels.get(location.logical_role)
        requested_classes = tuple(item.information_class for item in request.requested_information)
        if channels is None or len(requested_classes) != 1 or requested_classes[0] not in channels:
            raise ValueError("requested information does not match TIDMAD model-segment role")

        scope = self.deserialize_scope(request.requested_scope.serialized_scope)
        assert isinstance(scope, TidmadScope)
        profile = scope.profile or resolve_dataset_profile()
        topology = tidmad_topology(profile)
        psd_length = topology.dataset.psd_segment_length
        if psd_length % scope.seg_size:
            raise ValueError(
                "TIDMAD model-segment materialization requires segmentation_size "
                "to divide the task PSD segment length exactly"
            )
        rows_per_psd = psd_length // scope.seg_size
        row_identities = [
            (int(file_index), int(psd_index), row_index)
            for file_index in sorted(scope.sample_set, key=int)
            for psd_index in scope.sample_set[file_index]
            for row_index in range(rows_per_psd)
        ]
        total_available = len(row_identities)
        if total_available == 0:
            raise ValueError("TIDMAD model-segment scope contains no rows")
        policy = request.sampling_policy
        selected_count = total_available
        if policy.fraction is not None:
            selected_count = max(1, round(total_available * policy.fraction))
        if policy.max_items is not None:
            selected_count = min(selected_count, policy.max_items)
        if policy.mode == "representative" and policy.max_items is None and policy.fraction is None:
            selected_count = min(4, total_available)
        rng = np.random.default_rng(policy.seed)
        if policy.strategy in {"stratified", "task_defined"}:
            available_by_file = {
                int(file_index): len(scope.sample_set[file_index]) * rows_per_psd
                for file_index in sorted(scope.sample_set, key=int)
            }
            per_file = _stratified_analysis_indices(available_by_file, selected_count, rng)
            offsets: dict[int, int] = {}
            offset = 0
            for file_index, count in available_by_file.items():
                offsets[file_index] = offset
                offset += count
            selected_indices = np.asarray(
                [
                    offsets[file_index] + int(local_index)
                    for file_index, local_indices in per_file.items()
                    for local_index in local_indices
                ],
                dtype=np.int64,
            )
        elif selected_count == total_available:
            selected_indices = np.arange(total_available, dtype=np.int64)
        else:
            selected_indices = np.sort(
                rng.choice(total_available, size=selected_count, replace=False)
            )

        selected_rows: list[np.ndarray] = []
        selected_ids: list[str] = []
        data_root = resolve_physical_data_root()
        channel_name = getattr(topology.channels, channels[requested_classes[0]])
        handles: dict[int, h5py.File] = {}
        try:
            for selected_index in selected_indices.tolist():
                file_index, psd_index, row_index = row_identities[int(selected_index)]
                handle = handles.get(file_index)
                if handle is None:
                    source = (
                        Path(data_root)
                        / topology.dataset.validation_file_name(file_index)
                    )
                    handle = h5py.File(source, "r")
                    handles[file_index] = handle
                values = _h5_dataset(handle, "timeseries", channel_name, "timeseries")
                start = psd_index * psd_length + row_index * scope.seg_size
                stop = start + scope.seg_size
                selected_rows.append(
                    np.asarray(values[start:stop], dtype=np.int16)
                    + topology.encoding.value_offset
                )
                selected_ids.append(
                    f"validation-{file_index:04d}-psd-{psd_index:06d}-ml-{row_index:04d}"
                )
        finally:
            for handle in handles.values():
                handle.close()

        rows = np.stack(selected_rows)
        example_ids = np.asarray(selected_ids, dtype="U64")
        selection_sha = canonical_sha256({"example_ids": example_ids.tolist()})
        selection = CertifiedSelectionIdentity(
            selection_id=f"tidmad-model-segments-{selection_sha[:16]}",
            selection_sha256=selection_sha,
            sampling_policy_sha256=canonical_sha256(request.sampling_policy),
            sampling_mode=policy.mode,
            sampling_strategy=policy.strategy,
            sampling_seed=policy.seed,
            population_unit="validation model-input segments",
            total_available=total_available,
            selected_count=len(example_ids),
        )
        buffer = io.BytesIO()
        np.savez(
            buffer,
            example_ids=example_ids,
            **{f"information__{requested_classes[0]}": rows},
        )
        payload = buffer.getvalue()
        digest = hashlib.sha256(payload).hexdigest()
        logical_ref = f"opaque://tidmad-analysis/{request.binding_id}/{digest}"
        self._analysis_payload_store()[logical_ref] = payload
        return MaterializedAnalysisView(
            materialization_id=f"tidmad-{request.binding_id}-{digest[:16]}",
            invocation_id=request.invocation_id,
            binding_id=request.binding_id,
            slot_id=request.slot_id,
            asset_id=request.asset.asset_id,
            split_id=request.split_id,
            content_ref=CertifiedArtifactRef(
                logical_ref=logical_ref,
                sha256=digest,
                media_type="application/x-npz",
                byte_size=len(payload),
            ),
            format_id=request.requested_format_id,
            population_unit="validation model-input segments",
            total_available=total_available,
            materialized_count=len(example_ids),
            certified_information=request.requested_information,
            selection_identity=selection,
            task_data_path_id=self.task_data_path_id,
            source_digests=(digest,),
            authorization_receipt=authorized.authorization_receipt,
        )

    def export_analysis_materialization(
        self,
        content_ref: CertifiedArtifactRef,
        destination: Path,
    ) -> None:
        payload = self._analysis_payload_store().get(content_ref.logical_ref)
        if payload is None or hashlib.sha256(payload).hexdigest() != content_ref.sha256:
            raise ValueError("unknown or mismatched TIDMAD analysis materialization")
        destination.write_bytes(payload)

    @staticmethod
    def _scope(scope: object) -> TidmadScope:
        if not isinstance(scope, TidmadScope):
            raise TypeError(
                "TIDMAD data path requires a TidmadScope, got "
                f"{type(scope).__name__} — the binding and the scope object "
                "must come from the same task."
            )
        return scope

    def training_dataset(
        self, scope: object, params: EpochSamplingParams
    ) -> Dataset[Any]:
        s = self._scope(scope)
        # The caller's freeze-subsample choice is already folded into
        # ``epoch_seed`` (child §3); a None seed preserves the class's own
        # unseeded default.
        rng = (
            random.Random(params.epoch_seed) if params.epoch_seed is not None else None
        )
        return TIDMADEpochDataset(
            data_dir=params.data_dir,
            sample_set=s.sample_set,
            seg_size=s.seg_size,
            train_portion=params.train_portion,
            rng=rng,
            profile=s.profile,
            max_samples=params.max_samples,
        )

    def storage_read_scope(self, data_dir: str, scope: object) -> StorageReadScope:
        """Describe compressed source bytes for generic setup provenance."""
        s = self._scope(scope)
        profile = s.profile or resolve_dataset_profile()
        dataset = tidmad_topology(profile).dataset
        paths = tuple(
            os.path.abspath(
                os.path.join(data_dir, dataset.training_file_name(int(file_index)))
            )
            for file_index in sorted(s.sample_set, key=int)
        )
        expected_bytes = sum(
            round(
                os.path.getsize(path)
                * len(s.sample_set[file_index])
                / dataset.segments_per_file
            )
            for file_index, path in zip(sorted(s.sample_set, key=int), paths, strict=True)
            if os.path.isfile(path)
        )
        return StorageReadScope(
            file_paths=paths,
            expected_on_disk_bytes=expected_bytes,
        )

    # ------------------------------------------------------------------
    # TaskScopeCapability — the OPTIONAL sibling (Step 12 / PR-12bc B3)
    # ------------------------------------------------------------------
    #
    # Scope CONSTRUCTION for TIDMAD is `build_sample_set`, which already
    # exists and is already the authority. These methods RELOCATE the call;
    # they never copy the selection logic. The differential oracle in
    # `tests/unit/execute_tools/test_step12_pr12bc_b3_tidmad_capability.py`
    # is what proves that: a capability-built scope deep-equals the
    # legacy-built one for every cell of the matrix.

    #: The per-attempt task knob TIDMAD's scope needs and the framework has no
    #: vocabulary for: the planner's ML segmentation size. It rides the
    #: request's OPAQUE `task_parameters` (D-BC-1 extension, B3).
    _SEG_SIZE_PARAMETER: ClassVar[str] = "seg_size"

    def _build_scope(
        self, request: ScopeBuildRequest, *, strategy: str, seed: int | None
    ):
        profile = resolve_dataset_profile()
        seg_size = request.task_parameters.get(self._SEG_SIZE_PARAMETER)
        if not isinstance(seg_size, int) or seg_size <= 0:
            raise ValueError(
                f"TIDMAD scope construction requires a positive "
                f"{self._SEG_SIZE_PARAMETER!r} in the request's task_parameters "
                f"(the planner's ML segmentation size); got {seg_size!r}. The "
                f"framework has no vocabulary for it, so it must be declared by "
                f"the caller rather than guessed here."
            )
        sample_set = build_sample_set(
            # Both existing tuner call sites pass ``is_trial=True`` and differ
            # only in VALUES (`planning.py:397-414`); ``round_kind`` carries
            # which round those values came from, not a different code path.
            is_trial=True,
            trial_strategy=cast('Literal["snapshot", "anchors", "target"]', strategy),
            trial_portion=request.portion,
            target_files=list(request.target_partitions) or None,
            seed=seed,
            scope=DataScope.from_cli(request.subset_ref)
            if request.subset_ref
            else None,
            profile=profile,
        )
        return TidmadScope(sample_set=sample_set, seg_size=seg_size, profile=profile)

    def build_training_scope(self, request: ScopeBuildRequest) -> object:
        """The attempt's TRAINING scope, through the existing authority."""
        return self._build_scope(
            request, strategy=request.selection_strategy, seed=request.seed
        )

    def build_eval_scope(self, request: ScopeBuildRequest) -> object:
        """The attempt's EVALUATION scope.

        Formal-mode eval strategy is locked to ``snapshot``
        (``policy.py:1169``); the CALLER resolves that and hands it here, so
        this method does not re-decide policy it does not own.
        """
        return self._build_scope(
            request, strategy=request.selection_strategy, seed=request.seed
        )

    def validate_health_coverage(
        self, request: HealthCoverageRequest
    ) -> HealthCoverageResult:
        """Confirm every effective Health-monitored file is in this scope.

        An explicit monitored-file override is transparently transported by
        infra in the typed request. When it is absent, this task resolves its
        task-owned Health binding through the existing public composed-Health
        authority. Checks without an explicit peek use the established
        full-dataset scope contract; any unresolved demand fails closed.
        """
        scope = self._scope(request.evaluation_scope)
        monitored = request.health_gate_files
        if monitored is None:
            monitored = self._health_files_from_binding(request.health_binding, scope)
            if monitored is None:
                return HealthCoverageResult(
                    applicable=True,
                    covered=False,
                    reason=(
                        "TIDMAD Health coverage could not resolve the task's "
                        "effective monitored file set"
                    ),
                )
        present = {int(file_index) for file_index in scope.sample_set}
        missing = sorted(set(monitored) - present)
        if missing:
            return HealthCoverageResult(
                applicable=True,
                covered=False,
                reason=(
                    "TIDMAD Health monitored files are absent from the exact "
                    f"scope: {missing}"
                ),
            )
        return HealthCoverageResult(
            applicable=True,
            covered=True,
            reason=(
                "TIDMAD Health coverage includes every resolved monitored "
                f"file ({len(monitored)} files)"
            ),
        )

    @staticmethod
    def _health_files_from_binding(
        binding: object, scope: TidmadScope
    ) -> tuple[int, ...] | None:
        """Resolve default monitored files through the public Health loader."""
        if not isinstance(binding, str):
            return None
        try:
            config, _task_config, _plugins = load_composed_health_config(
                None, binding
            )
        except (OSError, TypeError, ValueError):
            return None
        demand: set[int] = set()
        partition_count = scope.profile.partition_count if scope.profile is not None else None
        if partition_count is None:
            return None
        for gate in config.health_gates:
            for check in gate.checks:
                configured = check.config.get("peek_file_indices")
                demand.update(
                    range(partition_count)
                    if not configured
                    else (int(index) for index in configured)
                )
        return tuple(sorted(demand))

    def trial_anchor_path(self, data_root: str) -> str:
        """TIDMAD's trial-anchoring artifact (B7, satellite (e)).

        The filename the tuner used to inline. It lives HERE now because it is
        TIDMAD's, which is what lets a task that has no such artifact refuse a
        trial round by name instead of failing on a filename it never declared.
        """
        return os.path.join(data_root, _TIDMAD_ANCHOR_MAP_NAME)

    def serialize_scope(self, scope: object) -> str:
        """CANONICAL bytes for a ``TidmadScope``.

        Canonical because the framework digests the result: ``sort_keys`` and
        the compact separators are the contract, not a formatting preference.
        Sample-set keys become STRINGS here, which is what JSON does anyway
        and what ``:375``'s ``int(k)`` already expects on the way back.
        """
        s = self._scope(scope)
        payload = {
            "kind": _TIDMAD_SCOPE_KIND,
            "sample_set": {str(k): list(v) for k, v in s.sample_set.items()},
            "seg_size": s.seg_size,
            "profile": s.profile.to_wire() if s.profile is not None else None,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def deserialize_scope(self, payload: str) -> object:
        """The inverse, FAIL-CLOSED.

        A payload this implementation did not write — another task's scope, a
        truncated file, a future version — RAISES naming what was wrong. It is
        never partially accepted, because a partially accepted scope trains on
        data nobody declared.
        """
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"TIDMAD scope payload is not valid JSON ({exc})."
            ) from exc
        if not isinstance(decoded, dict):
            raise ValueError(
                f"TIDMAD scope payload must be a JSON object, got {type(decoded).__name__}."
            )
        kind = decoded.get("kind")
        if kind != _TIDMAD_SCOPE_KIND:
            raise ValueError(
                f"scope payload declares kind {kind!r}, not {_TIDMAD_SCOPE_KIND!r} — "
                f"the binding and the scope object must come from the same task."
            )
        missing = [k for k in ("sample_set", "seg_size") if k not in decoded]
        if missing:
            raise ValueError(f"TIDMAD scope payload is missing {missing}.")
        raw_profile = decoded.get("profile")
        try:
            return TidmadScope(
                sample_set={int(k): list(v) for k, v in decoded["sample_set"].items()},
                seg_size=decoded["seg_size"],
                profile=(
                    DatasetProfile.model_validate(raw_profile)
                    if raw_profile is not None
                    else None
                ),
            )
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError(f"TIDMAD scope payload is malformed ({exc}).") from exc

    def validation_dataset(
        self, scope: object, params: EvalMaterializationParams
    ) -> Dataset[Any]:
        """Materialize the validation scope EXACTLY, failing closed.

        The exact-materialization check relocated verbatim from the engine's
        R3 pass (D14-1 C3; same ``ValidationScopeError``, same message, same
        trigger conditions — pinned by the 07a suite, which passes UNCHANGED).
        The requested side is pure arithmetic over the declared scope —
        identical to the engine preflight's formula — so a disk that changed
        mid-run surfaces as materialized ≠ requested, exactly as before.
        """
        s = self._scope(scope)
        profile = s.profile or resolve_dataset_profile()
        ds = TIDMADValidationDataset(
            data_dir=params.data_dir,
            sample_set=s.sample_set,
            seg_size=s.seg_size,
            profile=profile,
        )
        ml_segs_per_psd = (
            tidmad_topology(profile).dataset.psd_segment_length // s.seg_size
        )
        per_file_requested = {
            int(k): len(segments) * ml_segs_per_psd
            for k, segments in s.sample_set.items()
        }
        requested_rows = sum(per_file_requested.values())
        materialized = len(ds)
        per_file_materialized = {
            idx: end - start for idx, (start, end) in ds.file_row_ranges.items()
        }
        if (
            materialized != requested_rows
            or per_file_materialized != per_file_requested
        ):
            raise ValidationScopeError(
                f"validation scope materialized {materialized} ML rows "
                f"({per_file_materialized!r}) but {requested_rows} were requested "
                f"({per_file_requested!r}) — the declared scope must materialize exactly."
            )
        return ds

    def write_deliverable(
        self,
        outputs: Iterable[Any],
        request: DeliverableWriteRequest,
    ) -> None:
        """Persist legacy tuples or streamed composed predictions as ABRA files.

        The legacy caller supplies processed ``(file_index, denoised,
        injected)`` tuples. The composed caller supplies raw predictions in
        validation-dataset order together with the task scope and physical
        source context. Predictions are decoded and persisted one file at a
        time so full classification logits never accumulate in host memory.
        """
        if request.task_scope is not None or request.source_context is not None:
            self._write_streamed_predictions(outputs, request)
            return

        profile = resolve_dataset_profile()
        spec = derive_tidmad_deliverable_spec(profile)
        for file_index, denoised, injected in outputs:
            self._persist_file(
                file_index=int(file_index),
                denoised=np.asarray(denoised),
                injected=np.asarray(injected),
                request=request,
                spec=spec,
            )

    def _write_streamed_predictions(
        self,
        outputs: Iterable[Any],
        request: DeliverableWriteRequest,
    ) -> None:
        scope = self._scope(request.task_scope)
        context = request.source_context
        if context is None:
            raise ValueError("composed TIDMAD persistence requires source_context")

        dataset = self.validation_dataset(
            scope,
            EvalMaterializationParams(data_dir=context.data_dir),
        )
        if len(dataset) != context.sample_count:
            raise ValueError(
                f"TIDMAD deliverable source materialized {len(dataset)} samples, "
                f"but inference declared {context.sample_count}"
            )

        profile = scope.profile or resolve_dataset_profile()
        topology = tidmad_topology(profile)
        encoding = topology.encoding
        spec = derive_tidmad_deliverable_spec(profile)
        storage_np = np.dtype(spec.storage.storage_dtype)
        predictions = iter(outputs)
        consumed = 0

        for file_index, (start, end) in dataset.file_row_ranges.items():
            rows = end - start
            denoised = np.empty((rows, scope.seg_size), dtype=storage_np)
            for local_row in range(rows):
                try:
                    prediction = next(predictions)
                except StopIteration as exc:
                    raise ValueError(
                        f"TIDMAD inference produced {consumed} predictions, "
                        f"but {len(dataset)} were declared"
                    ) from exc
                if isinstance(prediction, torch.Tensor):
                    prediction_array = prediction.detach().cpu().numpy()
                else:
                    prediction_array = np.asarray(prediction)
                if (
                    prediction_array.ndim == 2
                    and prediction_array.shape[0] == encoding.num_classes
                ):
                    decoded = prediction_array.argmax(axis=0)
                elif prediction_array.ndim == 2 and prediction_array.shape[0] == 1:
                    decoded = prediction_array[0]
                elif prediction_array.ndim == 1:
                    decoded = prediction_array
                else:
                    raise ValueError(
                        "TIDMAD prediction must have shape [classes, time], "
                        f"[1, time], or [time]; got {prediction_array.shape}"
                    )
                if decoded.shape != (scope.seg_size,):
                    raise ValueError(
                        f"TIDMAD prediction has decoded shape {decoded.shape}; "
                        f"expected {(scope.seg_size,)}"
                    )
                denoised[local_row] = (decoded - encoding.value_offset).astype(
                    storage_np
                )
                consumed += 1

            self._persist_file(
                file_index=file_index,
                denoised=denoised,
                injected=(
                    dataset.materialize_storage_targets(start, end)
                    if isinstance(dataset, TIDMADValidationDataset)
                    else dataset.targets[start:end]
                ),
                request=request,
                spec=spec,
            )

        sentinel = object()
        if next(predictions, sentinel) is not sentinel:
            raise ValueError(
                f"TIDMAD inference produced more than the declared {len(dataset)} predictions"
            )
        if consumed != len(dataset):
            raise ValueError(
                f"TIDMAD inference produced {consumed} predictions, "
                f"but {len(dataset)} were declared"
            )

    @staticmethod
    def _persist_file(
        *,
        file_index: int,
        denoised: np.ndarray,
        injected: np.ndarray,
        request: DeliverableWriteRequest,
        spec: Any,
    ) -> None:
        storage_np = np.dtype(spec.storage.storage_dtype)
        out_name = os.path.join(
            request.output_dir,
            spec.naming.name(
                model_type=request.model_type,
                run_name=request.run_name,
                exp_id=request.exp_id,
                input_identity=file_index,
            ),
        )
        if os.path.exists(out_name):
            os.remove(out_name)
        create_abra_file(
            out_name,
            denoised.flatten().astype(storage_np),
            injected.flatten().astype(storage_np),
            indexed=False,
            storage=spec.storage,
        )

    def read_evaluation_payload(self, request: EvaluationReadRequest) -> object:
        """Resolve this run/experiment's persisted deliverables.

        Returns ``{file_index: absolute_path}`` for every file in
        ``deliverable_dir`` whose name round-trips EXACTLY through the naming
        authority for this (model_type, run_name, exp_id) — path resolution
        only; the Step-06 authority owns everything downstream. A missing
        directory yields ``{}`` (zero deliverables): absence is DATA for the
        Step-06 scoreability contract, which owns the structured refusal —
        never an infrastructure traceback here.
        """
        profile = resolve_dataset_profile()
        spec = derive_tidmad_deliverable_spec(profile)
        payload: dict[int, str] = {}
        if not os.path.isdir(request.deliverable_dir):
            return payload
        for entry in sorted(os.listdir(request.deliverable_dir)):
            file_index = spec.naming.input_identity_of(entry)
            if file_index is None:
                continue
            expected = spec.naming.name(
                model_type=request.model_type,
                run_name=request.run_name,
                exp_id=request.exp_id,
                input_identity=file_index,
            )
            if entry != expected:
                continue
            payload[file_index] = os.path.join(request.deliverable_dir, entry)
        return TaskEvaluationPayload(value=payload, deliverables=payload)
