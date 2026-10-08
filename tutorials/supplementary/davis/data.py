"""Frozen DAVIS clip identities and previews through the task-owned decoder."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import ModuleType

import yaml
from pydantic import BaseModel, ConfigDict

from tasks.davis_future_prediction.tools.fetch_davis import DAVIS_TRAINVAL_480P
from tutorials.shared.runtime import ROOT
from tutorials.supplementary.davis.settings import DavisExperiment

TASK = ROOT / "tasks/davis_future_prediction"


class ScopeCount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    role: str
    fraction: float
    seed: int
    clips: int
    sequences: int


def manifests(settings: DavisExperiment) -> Path:
    return settings.composition.parent.parent / "data/manifests"


def task_module(settings: DavisExperiment) -> ModuleType:
    """Reuse the composition-loaded module; a second import would re-register it."""
    task = selected_task(settings)
    return sys.modules[type(task).__module__]


def frame_files(settings: DavisExperiment) -> tuple[Path, ...]:
    """All Train/Validation first-window files, even for a smaller current scope."""
    owner = task_module(settings)
    return tuple(
        sorted(
            {
                owner.frame_path(
                    settings.data_dir, row.sequence_name, row.start_frame + offset
                )
                for role in ("train", "validation")
                for row in owner.load_davis_clips(
                    manifests(settings) / f"gate2_{role}.csv"
                )
                for offset in range(owner.WINDOW_FRAMES)
            }
        )
    )


def verify_files(settings: DavisExperiment, *, hashes: bool = False) -> dict:
    pack = settings.composition.parent.parent
    # This tutorial preserves the original split and decoder. New scientific
    # definitions require a separate task/experiment, not hidden preview semantics.
    for relative in (
        "runtime/davis_data_path.py",
        "data/manifests/SHA256SUMS",
        "data/manifests/sequences.csv",
        "data/manifests/gate2_train.csv",
        "data/manifests/gate2_validation.csv",
        "data/manifests/gate2_final.csv",
        "data/manifests/execution.json",
        "declared/task_health.yaml",
    ):
        if (pack / relative).read_bytes() != (TASK / relative).read_bytes():
            raise ValueError(
                f"Copied {relative} differs from the original DAVIS tutorial authority; restore it or define a separate scientific experiment"
            )
    owner = task_module(settings)
    rows = owner.load_davis_sequences(manifests(settings) / "sequences.csv")
    roles = {
        role: {r.sequence_name for r in rows if r.scope == role}
        for role in ("train", "validation", "final")
    }
    if any(
        roles[a] & roles[b]
        for a, b in (
            ("train", "validation"),
            ("train", "final"),
            ("validation", "final"),
        )
    ):
        raise ValueError("DAVIS sequence roles overlap")
    files = frame_files(settings)
    for path in files:
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(
                f"Missing or empty DAVIS frame: {path}. Reuse an extracted official dataset or follow the data setup guide's fetch --extract --check-layout command."
            )
    archive = settings.data_dir / DAVIS_TRAINVAL_480P.name
    if not archive.is_file():
        raise ValueError(
            f"Missing pinned archive: {archive}. Keep the official archive beside its extracted DAVIS directory; see the data setup guide."
        )
    probes = json.loads((manifests(settings) / "execution.json").read_text())["probes"]
    if hashes:
        with archive.open("rb") as stream:
            if (
                hashlib.file_digest(stream, "sha256").hexdigest()
                != DAVIS_TRAINVAL_480P.sha256
            ):
                raise ValueError("DAVIS archive SHA-256 differs from its official pin")
        train = owner.load_davis_clips(manifests(settings) / "gate2_train.csv")
        for row in train:
            key = f"{row.sequence_name}:{row.start_frame}"
            if (
                key in probes
                and owner.window_probe_sha256(settings.data_dir, row) != probes[key]
            ):
                raise ValueError(f"DAVIS decoded-window probe differs: {key}")
    return {
        "archive_bytes": archive.stat().st_size,
        "required_frame_files": len(files),
        "required_frame_bytes": sum(p.stat().st_size for p in files),
        "original_sequences": {role: len(names) for role, names in roles.items()},
        "verification": "archive_sha256_and_ten_decode_probes"
        if hashes
        else "frozen_manifests_and_frame_presence_only",
        "limits": "Archive verification does not prove every extracted frame matches it; ten decoded probes cover only their named windows. File metadata binds ordinary replacement for result reuse.",
    }


def selected_task(settings: DavisExperiment):
    from workflows.task_composition import compose_run_task_bindings

    declaration = yaml.safe_load(settings.composition.read_text())
    config = declaration.get("task_data_path", {}).get("config", {})
    expected = {
        "clips_path": {"ref": "../data/manifests/gate2_train.csv"},
        "eval_clips_path": {"ref": "../data/manifests/gate2_validation.csv"},
    }
    if config != expected:
        raise ValueError(
            "DAVIS tutorial requires original Train/Validation clip manifests; Final clips remain unbound"
        )
    if declaration.get("task_health") != {"config": "../declared/task_health.yaml"}:
        raise ValueError("DAVIS tutorial requires its original task Health declaration")
    binding = compose_run_task_bindings(str(settings.composition))
    original = yaml.safe_load((TASK / "declared/task_config.yaml").read_text())
    expected_contract = type(binding.forward_contract).model_validate(
        original["forward_contract"]
    )
    saved_path = Path(binding.provenance.source_paths["task_config"])
    saved_values = yaml.safe_load(saved_path.read_text())
    saved_contract = type(binding.forward_contract).model_validate(
        saved_values["forward_contract"]
    )
    if saved_contract != expected_contract:
        raise ValueError(
            "DAVIS tutorial requires the original 8-context/4-target forward contract; restore the copied declaration"
        )
    from workflows.task_config import assert_cached_task_config_source

    assert_cached_task_config_source(
        str(saved_path), hashlib.sha256(saved_path.read_bytes()).hexdigest()
    )
    if binding.task_data_path.task_data_path_id != "davis_future_prediction":
        raise ValueError("Select the DAVIS future-frame task")
    if (binding.objective.loss_type, binding.objective.loss_name) != (
        "custom",
        "davis_exact_l1",
    ):
        raise ValueError("DAVIS requires its task-owned exact-L1 objective")
    if (binding.metric.spec.id, binding.metric.spec.direction) != ("mse", "lower"):
        raise ValueError("DAVIS reports MSE (lower)")
    return binding.task_data_path


def scope_counts(settings: DavisExperiment, *, seed: int = 42) -> list[ScopeCount]:
    from execute_tools.task_data_path import ScopeBuildRequest

    verify_files(settings)
    task = selected_task(settings)
    reports = []
    for name, role, fraction, kind in (
        ("Trial training", "train", settings.trial_train_fraction, "trial"),
        ("Trial evaluation", "validation", settings.trial_eval_fraction, "trial"),
        ("Formal training", "train", settings.formal_train_fraction, "formal"),
        ("Formal evaluation", "validation", settings.formal_eval_fraction, "formal"),
    ):
        request = ScopeBuildRequest(
            round_kind=kind, selection_strategy="snapshot", portion=fraction, seed=seed
        )
        scope = (
            task.build_training_scope(request)
            if role == "train"
            else task.build_eval_scope(request)
        )
        reports.append(
            ScopeCount(
                name=name,
                role=role,
                fraction=fraction,
                seed=seed,
                clips=len(scope.rows),
                sequences=len({r.sequence_name for r in scope.rows}),
            )
        )
    return reports


def show_clip(settings: DavisExperiment):
    """Display all eight context and four target frames from the native dataset."""
    import matplotlib.pyplot as plt
    from execute_tools.task_data_path import EpochSamplingParams, ScopeBuildRequest

    verify_files(settings)
    task = selected_task(settings)
    scope = task.build_training_scope(
        ScopeBuildRequest(
            round_kind="trial",
            selection_strategy="snapshot",
            portion=settings.trial_train_fraction,
            seed=42,
        )
    )
    context, target = task.training_dataset(
        scope, EpochSamplingParams(data_dir=str(settings.data_dir), train_portion=1.0)
    )[0]
    figure, axes = plt.subplots(3, 4, figsize=(12, 6))
    for index, axis in enumerate(axes.flat):
        frame = context[:, index] if index < 8 else target[:, index - 8]
        axis.imshow(frame.permute(1, 2, 0).numpy(), vmin=0, vmax=1)
        axis.set_title(f"Context {index + 1}" if index < 8 else f"Target {index - 7}")
        axis.axis("off")
    clip = scope.rows[0]
    figure.suptitle(
        f"Train clip: {clip.sequence_name}, start={clip.start_frame}; actual task decoder"
    )
    figure.tight_layout()
    return figure
