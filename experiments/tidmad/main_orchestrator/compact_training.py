"""Read the baseline's compact training files using original task scope IDs."""

import hashlib
import importlib
import json
from pathlib import Path
from typing import ClassVar

import h5py
import numpy as np
from execute_tools.dataset_config import resolve_dataset_profile
from execute_tools.task_data_path import EpochSamplingParams, StorageReadScope
from workflows.task_composition import compose_task_data_path_from_manifest


def frozen_analysis_data_path(*, frozen_manifest: str):
    """Reuse the original frozen plugin identity for analysis and training.

    Loading the same frozen file through a relocated absolute reference gives
    the generic plugin loader a different module identity. Resolve through the
    original manifest, exactly as the compact training delegate does.
    """
    return compose_task_data_path_from_manifest(frozen_manifest)


class CompactFrozenPoolDataPath:
    """Keep original pool/validation semantics; translate training offsets only.

    This deployment adapter is selected explicitly for compact baseline data.
    Full original files are refused rather than silently reading wrong samples.
    """

    task_data_path_id: ClassVar[str] = "tidmad_compact_frozen_training_pool"

    def __init__(self, *, frozen_manifest: str):
        # Load the frozen task's implementation, not the current repository's
        # task class. Only its training storage interpretation is adapted.
        self._delegate = compose_task_data_path_from_manifest(frozen_manifest)
        self._topology = importlib.import_module(
            type(self._delegate).__module__
        ).tidmad_topology

    def __getattr__(self, name):
        return getattr(self._delegate, name)

    def validation_dataset(self, scope, params):
        return self._delegate.validation_dataset(scope, params)

    def write_deliverable(self, outputs, request):
        return self._delegate.write_deliverable(outputs, request)

    def read_evaluation_payload(self, request):
        return self._delegate.read_evaluation_payload(request)

    def _compact_scope(self, scope, data_dir):
        selected = self._delegate.deserialize_scope(
            self._delegate.serialize_scope(scope)
        )
        payload = self._POOL_PATH.read_bytes()
        if hashlib.sha256(payload).hexdigest() != self._POOL_SHA256:
            raise ValueError("TIDMAD frozen training pool manifest digest mismatch")
        pool = json.loads(payload)
        profile = selected.profile or resolve_dataset_profile()
        topology = self._topology(profile)
        if (
            pool["psd_segment_length"] != topology.dataset.psd_segment_length
            or pool["segments_per_file"] != topology.dataset.segments_per_file
        ):
            raise ValueError("compact training layout differs from declared geometry")
        mapped, physical = {}, []
        for file_index, indices in selected.sample_set.items():
            originals = pool["sample_set"][str(file_index)]
            positions = {original: local for local, original in enumerate(originals)}
            if any(index not in positions for index in indices):
                raise ValueError(
                    "training scope selects a segment outside the frozen pool"
                )
            mapped[file_index] = [positions[index] for index in indices]
            path = (
                Path(data_dir) / topology.dataset.training_file_name(int(file_index))
            ).resolve(strict=True)
            expected = len(originals) * topology.dataset.psd_segment_length
            with h5py.File(path, "r") as source:
                for channel in (
                    topology.channels.input_channel,
                    topology.channels.target_channel,
                ):
                    dataset = source[f"timeseries/{channel}/timeseries"]
                    if dataset.shape != (expected,) or dataset.dtype != np.dtype(
                        topology.encoding.storage_dtype
                    ):
                        raise ValueError(
                            "public training file is not the compact frozen layout"
                        )
            physical.append((path, len(indices), len(originals)))
        return selected.model_copy(update={"sample_set": mapped}), physical

    def training_dataset(self, scope, params: EpochSamplingParams):
        compact, _ = self._compact_scope(scope, params.data_dir)
        return self._delegate.training_dataset(compact, params)

    def storage_read_scope(self, data_dir: str, scope) -> StorageReadScope:
        _, physical = self._compact_scope(scope, data_dir)
        return StorageReadScope(
            file_paths=tuple(str(path) for path, _, _ in physical),
            expected_on_disk_bytes=sum(
                round(path.stat().st_size * selected / available)
                for path, selected, available in physical
            ),
        )
