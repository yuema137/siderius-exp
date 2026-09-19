"""Package a native candidate for the existing frozen CLI evaluator."""

import json
import shutil
from collections.abc import Sequence
from pathlib import Path

import torch
from agent.schemas.hyperparam_tuning import ExperimentRecord

from deployments.tidmad_coding_agent_baseline.tools.archive_candidate import (
    candidate_tree_digest,
    validate_candidate_source,
)
from deployments.tidmad_coding_agent_baseline.tools.segment_inference import (
    SegmentModelContract,
    load_candidate_model,
)
from experiments.shared.native_model_restore import restore_native_model
from experiments.shared.scripted_model_export import export_scripted_model


def package_native_candidate(
    *,
    root: Path,
    record: ExperimentRecord,
    approved_plugin: Path,
    contract: SegmentModelContract,
    examples: Sequence[tuple[torch.Tensor, ...]],
    destination: Path,
) -> str:
    """Return the candidate-tree digest after export and frozen-loader checks.

    Call only inside the research worker boundary. This does not submit, score
    or promote the model. No sample or raw data is retained in the candidate.
    """
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    if contract.output_kind != "continuous_regression":
        raise ValueError("main orchestrator requires the frozen regression contract")
    reference = record.trained_model_artifact_ref
    if reference is None:
        raise ValueError("native candidate has no certified trained-model reference")
    for args in examples:
        if (
            len(args) != 1
            or args[0].dtype != torch.int64
            or args[0].device.type != "cpu"
            or args[0].ndim != 2
            or args[0].shape[1] != contract.segment_size
            or not 1 <= args[0].shape[0] <= contract.inference_batch_size
        ):
            raise ValueError(
                "export examples must obey the frozen evaluator input contract"
            )
    with restore_native_model(
        root=root, reference=reference, approved_plugin=approved_plugin
    ) as restored:
        artifact = restored.artifact
        for tensor, required_dtype in (
            (artifact.model_io_contract.input, "int64"),
            (artifact.model_io_contract.output, "float32"),
        ):
            if (
                len(tensor.axes) != 2
                or required_dtype not in tensor.dtype.admissible
                or tensor.axes[1].dimension.fixed not in (None, contract.segment_size)
                or any(
                    tensor.axes[0].dimension.fixed not in (None, args[0].shape[0])
                    for args in examples
                )
            ):
                raise ValueError(
                    "certified tensor contract conflicts with evaluator contract"
                )
        if (
            artifact.training_run.experiment_id != record.exp_id
            or artifact.model_plugin_identity.model_type != record.model_type
            or json.loads(restored.config) != record.params.get("model_config")
        ):
            raise ValueError(
                "native record/config does not identify the certified model"
            )
        export_scripted_model(
            restored.model, examples=examples, destination=destination
        )
        try:
            (destination / "model.py").write_bytes(restored.source)
            (destination / "native_artifact.json").write_bytes(restored.descriptor)
            (destination / "native_model_config.json").write_bytes(restored.config)
            architecture = contract.model_dump(mode="json")
            architecture["native_model_type"] = record.model_type
            architecture["native_model_config"] = json.loads(restored.config)
            (destination / "architecture.json").write_text(
                json.dumps(architecture, indent=2)
            )
            training = {
                "proposed_train_config": record.params.get("train_config"),
                "loss_config": record.params.get("loss_config"),
                "training_history": (
                    record.training_history.model_dump(mode="json")
                    if record.training_history is not None
                    else None
                ),
                "training_scope": artifact.training_scope.model_dump(mode="json"),
            }
            (destination / "train_config.json").write_text(
                json.dumps(training, indent=2)
            )
            (destination / "native_provenance.json").write_text(
                json.dumps(
                    {
                        "artifact_ref": reference.model_dump(mode="json"),
                        "model_plugin_identity": artifact.model_plugin_identity.model_dump(
                            mode="json"
                        ),
                        "environment_identity": artifact.environment_identity.model_dump(
                            mode="json"
                        ),
                        "training_run": artifact.training_run.model_dump(mode="json"),
                        "qualification": "serialization_only_not_scored",
                    },
                    indent=2,
                )
            )
            loaded, _ = load_candidate_model(destination, torch.device("cpu"))
            with torch.inference_mode():
                for args in examples:
                    output = loaded(*args)
                    if (
                        not isinstance(output, torch.Tensor)
                        or output.shape != args[0].shape
                        or output.dtype != torch.float32
                        or not torch.isfinite(output).all()
                    ):
                        raise ValueError(
                            "exported output violates the frozen regression contract"
                        )
            validate_candidate_source(destination)
            return candidate_tree_digest(destination)
        except BaseException:
            shutil.rmtree(destination)
            raise
