"""CPDB source identity and previews through the unchanged task-owned graph loader."""

from __future__ import annotations

import hashlib
from typing import Literal

import h5py
import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field

from tutorials.shared.runtime import ROOT
from tutorials.supplementary.cancer.settings import CancerExperiment

SOURCE_MANIFEST = (
    ROOT / "tasks/cancer_gene_identification/declared/tutorial_source_files.json"
)


class SourceFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["cancer-cpdb-source-v1"]
    dataset: Literal["FrontisAI/NatureBench"]
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_path: Literal["tasks/s41551-024-01312-5/problem/data/cpdb/data.h5"]
    relative_path: Literal["cpdb/data.h5"]
    bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ScopeCount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    role: str
    label_fraction: float
    seed: int
    graphs: int
    nodes: int
    records: int
    active_labels: int
    negative: int
    positive: int


def verify_files(settings: CancerExperiment, *, hashes: bool = False) -> dict:
    declared = (
        settings.composition.parent.parent / "declared/tutorial_source_files.json"
    )
    source = SourceFile.model_validate_json(declared.read_text())
    if source != SourceFile.model_validate_json(SOURCE_MANIFEST.read_text()):
        raise ValueError(
            "Copied tutorial_source_files.json differs from the official authority; restore it"
        )
    path = settings.data_dir / source.relative_path
    if not path.is_file() or path.stat().st_size != source.bytes:
        raise ValueError(
            f"Missing or wrong-sized CPDB file: {path}. Follow the Cancer setup guide; reuse an existing official file or download only the pinned CPDB file."
        )
    if hashes:
        with path.open("rb") as stream:
            observed = hashlib.file_digest(stream, "sha256").hexdigest()
        if observed != source.sha256:
            raise ValueError(
                "CPDB SHA-256 differs from the pinned official source; do not train on this file"
            )
    with h5py.File(path, "r") as handle:
        required = {
            "features",
            "network",
            "mask_train",
            "mask_val",
            "mask_test",
            "y_train",
            "y_val",
        }
        if missing := required.difference(handle):
            raise ValueError(
                f"CPDB is missing required HDF5 datasets: {sorted(missing)}"
            )
        features = handle["features"]
        if len(features.shape) != 2 or features.shape[1] != 64:
            raise ValueError("CPDB features must have shape [nodes, 64]")
        nodes = features.shape[0]
        if handle["network"].shape != (nodes, nodes):
            raise ValueError("CPDB adjacency must match the complete node population")
        masks = {
            split: np.asarray(handle[f"mask_{split}"]).reshape(-1).astype(bool)
            for split in ("train", "val", "test")
        }
        if any(len(mask) != nodes or not mask.any() for mask in masks.values()):
            raise ValueError(
                "CPDB masks must cover the graph shape and each contain nodes"
            )
        if any(
            np.any(masks[a] & masks[b])
            for a, b in (("train", "val"), ("train", "test"), ("val", "test"))
        ):
            raise ValueError("CPDB original Train/Validation/Test masks overlap")
        for split in ("train", "val"):
            labels = np.asarray(handle[f"y_{split}"]).reshape(-1)
            if len(labels) != nodes or not np.isin(labels[masks[split]], [0, 1]).all():
                raise ValueError(
                    f"CPDB {split} labels must be binary on the original mask"
                )
    return {
        "source_files": 1,
        "bytes": source.bytes,
        "nodes": nodes,
        "original_masks": {key: int(value.sum()) for key, value in masks.items()},
        "verification": "sha256_and_structure" if hashes else "size_and_structure_only",
    }


def selected_task(settings: CancerExperiment):
    from workflows.task_composition import compose_run_task_bindings

    declaration = yaml.safe_load(settings.composition.read_text())
    if declaration.get("task_health") != {"none": True}:
        raise ValueError("Cancer tutorial requires its explicit no-Health declaration")
    config = declaration.get("task_data_path", {}).get("config", {})
    if config != {"instances": ["cpdb"], "evaluation_split": "val"}:
        raise ValueError(
            "This tutorial supports only complete CPDB with original validation masks; other networks or test scoring require a separate experiment"
        )
    if declaration.get("parameter_rules", {}).get("train_config.batch_size") != {
        "exact": 1
    }:
        raise ValueError(
            "CPDB is one complete graph per sample: batch_size must remain exactly 1"
        )
    binding = compose_run_task_bindings(str(settings.composition))
    if (
        binding.task_data_path.task_data_path_id != "naturebench_cancer_gene"
        or binding.task_data_path.max_inference_batch_size() != 1
    ):
        raise ValueError("Select the Cancer graph task with inference batch size 1")
    if (binding.objective.loss_type, binding.objective.loss_name) != (
        "custom",
        "cancer_gene_masked_bce",
    ):
        raise ValueError("Cancer tutorial requires the task-owned masked BCE objective")
    if (binding.metric.spec.id, binding.metric.spec.direction) != (
        "mean_auprc",
        "higher",
    ):
        raise ValueError("Cancer tutorial reports mean_auprc (higher)")
    return binding.task_data_path


def materialize(
    settings: CancerExperiment, *, role: str, fraction: float, seed: int = 42
):
    """Materialize exactly one graph via native scope/epoch fraction ownership."""
    from execute_tools.task_data_path import (
        EpochSamplingParams,
        EvalMaterializationParams,
        ScopeBuildRequest,
    )

    path = selected_task(settings)
    request = ScopeBuildRequest(
        round_kind="trial",
        selection_strategy="snapshot",
        portion=1 if role == "train" else fraction,
        seed=seed,
    )
    if role == "train":
        dataset = path.training_dataset(
            path.build_training_scope(request),
            EpochSamplingParams(
                data_dir=str(settings.data_dir), train_portion=fraction, epoch_seed=seed
            ),
        )
    elif role == "validation":
        dataset = path.validation_dataset(
            path.build_eval_scope(request),
            EvalMaterializationParams(data_dir=str(settings.data_dir)),
        )
    else:
        raise ValueError(
            "Only train and validation previews are supported; test labels remain unused"
        )
    return dataset[0]


def scope_counts(settings: CancerExperiment, *, seed: int = 42) -> list[ScopeCount]:
    verify_files(settings)
    reports = []
    for name, role, fraction in (
        ("Trial training", "train", settings.trial_train_label_fraction),
        ("Trial evaluation", "validation", settings.trial_eval_label_fraction),
        ("Formal training", "train", settings.formal_train_label_fraction),
        ("Formal evaluation", "validation", settings.formal_eval_label_fraction),
    ):
        tensor, target = materialize(settings, role=role, fraction=fraction, seed=seed)
        selected = (target[:, 0] == 1) & (target[:, 1] == 1)
        labels = target[selected, 2].numpy()
        reports.append(
            ScopeCount(
                name=name,
                role=role,
                label_fraction=fraction,
                seed=seed,
                graphs=1,
                nodes=int((tensor[:, 0] == 1).sum()),
                records=len(tensor),
                active_labels=len(labels),
                negative=int((labels == 0).sum()),
                positive=int((labels == 1).sum()),
            )
        )
    return reports


def show_graph(settings: CancerExperiment):
    """Visualize Train features and a topology crop, never a reduced execution graph."""
    import matplotlib.pyplot as plt

    verify_files(settings)
    tensor, _ = materialize(
        settings, role="train", fraction=settings.trial_train_label_fraction
    )
    nodes = tensor[tensor[:, 0] == 1]
    active = nodes[nodes[:, 3] == 1][:32]
    crop_size = min(64, len(nodes))
    edges = tensor[tensor[:, 0] == 0, 1:3].numpy().astype(np.int64)
    edges = edges[(edges < crop_size).all(axis=1)]
    crop = np.zeros((crop_size, crop_size), dtype=bool)
    crop[edges[:, 0], edges[:, 1]] = True
    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    image = axes[0].imshow(
        active[:, 4:].numpy(), aspect="auto", interpolation="nearest", cmap="viridis"
    )
    axes[0].set(
        xlabel="Multi-omics feature (64 columns)",
        ylabel="Selected Train node",
        title=f"CPDB: first {len(active)} active Train nodes",
    )
    figure.colorbar(image, ax=axes[0], label="Feature value")
    axes[1].imshow(crop, interpolation="nearest", cmap="Greys", vmin=0, vmax=1)
    axes[1].set(
        xlabel="Destination node",
        ylabel="Source node",
        title=f"Topology crop: first {crop_size} nodes\nVisualization only; execution uses the complete graph",
    )
    figure.tight_layout()
    return figure
