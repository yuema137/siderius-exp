"""Full-scope inference for Stage-1 winners before final Gold scoring."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Protocol

from pydantic import BaseModel, ConfigDict, Field

from core.sandbox_executor import (
    TidmadSandbox,
    get_loss_dir,
    get_plugin_dir,
    sandbox_models_dir,
)
from core.iteration_manifest import sha256_file
from execute_tools.dataset_config import DataScope
from execute_tools.deliverable_spec import DeliverableNaming, DeliverableStorage
from execute_tools.hdf5_deliverable import is_complete_hdf5_deliverable
from execute_tools.evaluation_metric import MetricSpec
from ml_models.loss_models_sandbox import register_loss_in_memory
from ml_models.plugin_loader import register_model_in_memory
from workflows.task_composition import (
    bind_run_task_composition,
    compose_run_task_bindings,
)

from tasks.tidmad.runtime.profile import tidmad_topology


class FullInferenceError(RuntimeError):
    """A winner cannot produce a complete full-scope deliverable set."""


class _Composer(Protocol):
    def __call__(
        self,
        deliverable_dirs: list[str],
        *,
        files: range,
        sample_set: None,
        reconciled_spec: MetricSpec,
        **kwargs: object,
    ) -> tuple[list[float], float]: ...


def bind_full_scope_composer(
    composer: _Composer, *, raw_data_dir: str
) -> _Composer:
    """Bind the existing shared scorer to one explicit raw-data root."""

    def score(
        deliverable_dirs: list[str],
        *,
        files: range,
        sample_set: None,
        reconciled_spec: MetricSpec,
        **_kwargs: object,
    ) -> tuple[list[float], float]:
        return composer(
            deliverable_dirs,
            files=files,
            sample_set=sample_set,
            reconciled_spec=reconciled_spec,
            raw_data_dir=raw_data_dir,
        )

    return score


class FullInferenceCandidate(BaseModel):
    """Persisted winner state required to replay inference without training."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    band: str
    source_workspace: str
    source_base_dir: str
    exp_id: str
    run_name: str
    model_type: str
    checkpoint_sha256: str
    resolved_model_config: dict = Field(
        validation_alias="model_config",
        serialization_alias="model_config",
    )
    loss_config: dict
    inference_batch: int | None = None
    file_indices: tuple[int, ...]


def _copy_plugin_family(
    source: str,
    destination: str,
    register: Callable[[str], str | None],
) -> None:
    """Copy and register one run-scoped plugin family."""
    if not os.path.isdir(source):
        return
    os.makedirs(destination, exist_ok=True)
    for entry in sorted(Path(source).glob("*.py")):
        target = os.path.join(destination, entry.name)
        shutil.copy2(entry, target)
        if register(target) is None:
            raise FullInferenceError(f"could not register staged plugin: {target}")


def _stage_candidate(candidate: FullInferenceCandidate, target: str) -> None:
    """Stage the exact checkpoint and run-scoped plugins into Stage 3."""
    source_models = sandbox_models_dir(candidate.source_base_dir)
    target_models = sandbox_models_dir(target)
    checkpoint_name = f"model_{candidate.model_type}_{candidate.exp_id}_agent.pth"
    sentinel_name = f"_OK_{candidate.exp_id}"
    for name in (checkpoint_name, sentinel_name):
        source = os.path.join(source_models, name)
        if not os.path.isfile(source):
            raise FullInferenceError(
                f"winner {candidate.band} is missing checkpoint evidence: {source}"
            )
        shutil.copy2(source, os.path.join(target_models, name))
    source_checkpoint = os.path.join(source_models, checkpoint_name)
    if sha256_file(source_checkpoint) != candidate.checkpoint_sha256:
        raise FullInferenceError(
            f"winner {candidate.band} checkpoint identity changed before replay: "
            f"{source_checkpoint}"
        )
    staged_checkpoint = os.path.join(target_models, checkpoint_name)
    if sha256_file(staged_checkpoint) != candidate.checkpoint_sha256:
        raise FullInferenceError(
            f"winner {candidate.band} staged checkpoint identity mismatch: "
            f"{staged_checkpoint}"
        )

    _copy_plugin_family(
        get_plugin_dir(candidate.source_base_dir, candidate.run_name),
        get_plugin_dir(target, candidate.run_name),
        register_model_in_memory,
    )
    _copy_plugin_family(
        get_loss_dir(candidate.source_base_dir, candidate.run_name),
        get_loss_dir(target, candidate.run_name),
        register_loss_in_memory,
    )


def run_full_inference(
    candidate: FullInferenceCandidate,
    *,
    output_root: str,
    data_dir: str,
    task_manifest: str,
) -> dict[int, str]:
    """Run the proven inference executor over all 200 segments per band file."""
    target = os.path.join(output_root, f"band_{candidate.band}")
    if os.path.exists(target):
        raise FullInferenceError(
            f"Stage-3 inference target already exists: {target}; use a fresh output root"
        )
    composition = compose_run_task_bindings(task_manifest)
    naming = composition.deliverable_naming
    if not isinstance(naming, DeliverableNaming):
        raise FullInferenceError(
            "Stage-3 task composition lacks indexed deliverable naming"
        )
    topology = tidmad_topology(composition.dataset_profile)
    segments_per_file = topology.dataset.segments_per_file
    storage = DeliverableStorage(
        input_channel_group=topology.channels.input_channel,
        target_channel_group=topology.channels.target_channel,
        storage_dtype=topology.encoding.storage_dtype,
        value_offset=topology.encoding.value_offset,
    )
    scope = DataScope.from_cli(candidate.band)
    full_sample_set = {
        index: list(range(segments_per_file)) for index in candidate.file_indices
    }
    os.makedirs(output_root, exist_ok=True)
    staged = tempfile.mkdtemp(prefix=f".band_{candidate.band}.", dir=output_root)
    with bind_run_task_composition(composition, physical_data_root=data_dir):
        sandbox = TidmadSandbox(
            run_name=candidate.run_name,
            workspace=staged,
            file_index=candidate.file_indices[0],
            data_scope=scope,
            deliverable_naming=naming,
        )
        _stage_candidate(candidate, staged)
        result = sandbox.execute_inference(
            exp_id=candidate.exp_id,
            run_name=candidate.run_name,
            model_type=candidate.model_type,
            m_cfg=candidate.resolved_model_config,
            l_cfg=candidate.loss_config,
            sample_set=full_sample_set,
            inference_batch=candidate.inference_batch,
        )
    if result.get("status") != "success":
        raise FullInferenceError(
            f"winner {candidate.band} full inference failed in {staged}: "
            f"{result.get('message', result)}"
        )

    relative_paths: dict[int, str] = {}
    expected_samples = segments_per_file * topology.dataset.psd_segment_length
    for index in candidate.file_indices:
        name = naming.name(
            model_type=candidate.model_type,
            run_name=candidate.run_name,
            exp_id=candidate.exp_id,
            input_identity=index,
        )
        path = os.path.join(staged, name)
        if not is_complete_hdf5_deliverable(path, expected_samples, storage):
            raise FullInferenceError(
                f"winner {candidate.band} full inference produced an incomplete "
                f"{segments_per_file}-segment deliverable for file {index}: {path}"
            )
        relative_paths[index] = name

    os.rename(staged, target)
    return {index: os.path.join(target, name) for index, name in relative_paths.items()}
