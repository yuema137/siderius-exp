"""Admit TIDMAD validation scope against operator-selected public task settings.

This task adapter belongs to experiment deployment. It opens no data files and
changes no frozen task package. The generic validation transport never reads
TIDMAD scope fields. Caller identity and native source admission remain separate.
"""

from pathlib import Path
from typing import cast

from execute_tools.dataset_config import DataScope, DatasetProfile, bind_dataset_profile
from execute_tools.scoring_utils import validate_sample_set
from execute_tools.task_data_path import bind_task_data_path
from pydantic import BaseModel, ConfigDict, Field

from experiments.shared.native_training_inputs import CapturedNativeInputs
from experiments.tidmad.main_orchestrator.validation_rows import declared_rows
from tasks.tidmad.runtime.profile import tidmad_topology
from tasks.tidmad.runtime.tidmad_data_path import TidmadScope, TidmadTaskDataPath


class AdmittedTidmadValidationScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    payload: str
    rows: int = Field(gt=0)


def admit_validation_scope(
    payload: str,
    *,
    profile: DatasetProfile,
    allowed_scope: DataScope,
    model_segmentation_size: int,
) -> AdmittedTidmadValidationScope:
    """Use the existing task decoder, range validator and row declaration.

    The operator supplies the profile/band; the model size comes from captured
    native configuration metadata. Omitted scope profile retains the task's
    existing explicit-bound-profile behavior, not an invented scientific default.
    Install that same profile binding during private materialization as well.
    """
    task = TidmadTaskDataPath()
    scope = cast(TidmadScope, task.deserialize_scope(payload))
    if scope.profile is not None and scope.profile != profile:
        raise ValueError("validation scope profile differs from operator task profile")
    if scope.seg_size != model_segmentation_size:
        raise ValueError(
            "validation segmentation differs from native model configuration"
        )
    if tidmad_topology(profile).dataset.psd_segment_length % scope.seg_size:
        raise ValueError("validation segmentation does not divide the task PSD length")
    validate_sample_set(scope.sample_set, scope=allowed_scope, profile=profile)
    with bind_dataset_profile(profile), bind_task_data_path(task):
        rows = declared_rows(scope)
    return AdmittedTidmadValidationScope(payload=task.serialize_scope(scope), rows=rows)


def admit_captured_validation_scope(
    captured: CapturedNativeInputs,
    *,
    manifest: Path,
    manifest_sha256: str,
    task_data_path_id: str,
    source_cwd: Path,
    profile: DatasetProfile,
    allowed_scope: DataScope,
    model_segmentation_size: int,
) -> AdmittedTidmadValidationScope:
    """Bind captured native task arguments to the operator's frozen task.

    The launcher creates the capture itself and protects the manifest and its
    referenced task files for the whole job. This checks selection and bytes,
    not filesystem ownership or researcher identity. Only the validation leg
    is authorized here; training sample selection remains native-owned.
    """
    import hashlib

    from execute_tools.scope_artifact import read_scope_artifact
    from execute_tools.training_cli import build_training_parser

    args = build_training_parser().parse_args(captured.command[2:])
    if args.task_manifest is None:
        raise ValueError("validation invocation omitted the operator task manifest")
    selected = Path(args.task_manifest)
    if not selected.is_absolute():
        selected = source_cwd / selected
    if selected.resolve(strict=True) != manifest.resolve(strict=True):
        raise ValueError("validation invocation selected a different task manifest")
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != manifest_sha256:
        raise ValueError("operator task manifest changed after admission")
    if args.task_data_path_id != task_data_path_id:
        raise ValueError("validation invocation selected a different task adapter")
    files = {item.argument: item for item in captured.files}

    def read_captured(name: str) -> bytes:
        item = files.get(name)
        if item is None or getattr(args, name) != str(item.captured):
            raise ValueError(f"validation invocation lacks captured {name}")
        payload = item.captured.read_bytes()
        if hashlib.sha256(payload).hexdigest() != item.sha256:
            raise ValueError(f"captured {name} changed before task admission")
        return payload

    if args.dataset_profile_json is not None:
        selected_profile = DatasetProfile.model_validate_json(
            read_captured("dataset_profile_json")
        )
        if selected_profile != profile:
            raise ValueError("captured profile differs from operator task profile")
    # Check captured identity and the task's separate scope transport digest.
    read_captured("task_eval_scope_ref")
    payload = read_scope_artifact(args.task_eval_scope_ref, args.task_eval_scope_digest)
    return admit_validation_scope(
        payload,
        profile=profile,
        allowed_scope=allowed_scope,
        model_segmentation_size=model_segmentation_size,
    )
