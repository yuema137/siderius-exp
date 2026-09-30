"""Create a new TESS task/data pair by regrouping only released train+validation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from tutorials.paper.runner import ROOT, TutorialExperiment, disjoint, verify_data
from tutorials.paper.task_view import inspect_task


class IdentityRow(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    split: Literal["train", "val"]
    gaia_id: int
    tic: int
    sector: int
    frot: float
    frot_err: float

    @property
    def key(self) -> str:
        return f"{self.gaia_id}:{self.sector}"


class SplitChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    validation_fraction: float = Field(default=0.2, gt=0, lt=1)
    seed: int = Field(default=42, ge=0)


class SplitPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choice: SplitChoice
    train_stars: int
    validation_stars: int
    train_curves: int
    validation_curves: int
    validation_gaia_ids: tuple[int, ...]


def read_rows(task: Path) -> list[IdentityRow]:
    with (task / "data/manifests/rotation_identity.csv").open(newline="") as stream:
        rows = [IdentityRow.model_validate(row) for row in csv.DictReader(stream)]
    if len({row.key for row in rows}) != len(rows):
        raise ValueError("duplicate curve identity in the input manifest")
    return rows


def choose_split(rows: list[IdentityRow], choice: SplitChoice) -> SplitPreview:
    """Choose complete stars, never individual curves, with a reproducible seed."""
    stars = sorted({row.gaia_id for row in rows})
    if len(stars) < 2:
        raise ValueError("a split requires at least two different stars")
    count = min(
        len(stars) - 1, max(1, math.ceil(len(stars) * choice.validation_fraction))
    )
    positions = np.random.default_rng(choice.seed).permutation(len(stars))[:count]
    selected = {stars[int(position)] for position in positions}
    val_curves = sum(row.gaia_id in selected for row in rows)
    return SplitPreview(
        choice=choice,
        train_stars=len(stars) - count,
        validation_stars=count,
        train_curves=len(rows) - val_curves,
        validation_curves=val_curves,
        validation_gaia_ids=tuple(sorted(selected)),
    )


def resplit_task(
    experiment: TutorialExperiment,
    task_output: Path,
    data_output: Path,
    choice: SplitChoice,
) -> SplitPreview:
    """Write new copies plus provenance; original task/data and test stay untouched."""
    if experiment.composition is None:
        raise ValueError("select the source task composition")
    source_task = experiment.composition.parents[1]
    canonical = source_task / "compositions/rotation_regression.yaml"
    if experiment.composition != canonical:
        raise ValueError("resplit exercise requires the standard TESS package layout")
    task_output, data_output = task_output.resolve(), data_output.resolve()
    for dest in (task_output, data_output):
        if dest.exists():
            raise ValueError("split outputs must be new; choose a new variant name")
        if any(
            not disjoint(dest, src)
            for src in (
                ROOT,
                experiment.infra_checkout,
                source_task,
                experiment.data_dir,
            )
        ):
            raise ValueError(
                "split outputs must be separate from both repositories and source inputs"
            )
    if not disjoint(task_output, data_output):
        raise ValueError("task copy and data output must be separate")
    rows = read_rows(source_task)
    populations = inspect_task(experiment).populations()
    for split in ("train", "val"):
        if {row.key for row in rows if row.split == split} != populations[split]:
            raise ValueError(
                "composition scopes differ from the standard identity manifest"
            )
    parent_data_hashes = verify_data(experiment.data_dir, populations)
    preview = choose_split(rows, choice)
    val_stars = set(preview.validation_gaia_ids)
    new_rows = [
        IdentityRow.model_validate(
            {
                **row.model_dump(),
                "split": "val" if row.gaia_id in val_stars else "train",
            }
        )
        for row in rows
    ]
    curves = {}
    for split in ("train", "val"):
        with np.load(
            experiment.data_dir / f"tess_rotation_{split}.npz", allow_pickle=False
        ) as archive:
            curves.update({key: archive[key].copy() for key in archive.files})
    shutil.copytree(
        source_task, task_output, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    manifest = task_output / "data/manifests/rotation_identity.csv"
    with manifest.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(IdentityRow.model_fields))
        writer.writeheader()
        writer.writerows(row.model_dump() for row in new_rows)
    data_output.mkdir(parents=True)
    for split in ("train", "val"):
        np.savez_compressed(
            data_output / f"tess_rotation_{split}.npz",
            **{row.key: curves[row.key] for row in new_rows if row.split == split},
        )
    profile_path = task_output / "declared/dataset_profile.json"
    profile = json.loads(profile_path.read_text())
    profile["topology"]["populations"].update(
        train=preview.train_curves, val=preview.validation_curves
    )
    profile["topology"]["tutorial_resplit"] = {
        **choice.model_dump(),
        "unit": "whole Gaia stars from released train+val only",
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "paper_comparable": False,
    }
    profile_path.write_text(json.dumps(profile, indent=2) + "\n")
    receipt = {
        "preview": preview.model_dump(),
        "parent_manifest_sha256": hashlib.sha256(
            (source_task / "data/manifests/rotation_identity.csv").read_bytes()
        ).hexdigest(),
        "parent_data_sha256": parent_data_hashes,
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "test_used": False,
        "paper_comparable": False,
    }
    (task_output / "resplit_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    with (task_output / "README.md").open("r+") as stream:
        original = stream.read()
        stream.seek(0)
        stream.write(
            "# Local re-split task variant\n\n"
            f"This copy has {preview.train_curves} training and {preview.validation_curves} "
            "validation curves. See `resplit_receipt.json` for its identity. "
            "The inherited description below documents the original release; "
            "its original population/count claims do not describe this variant.\n\n"
            + original
        )
    verify_data(
        data_output,
        {
            split: {r.key for r in new_rows if r.split == split}
            for split in ("train", "val")
        },
    )
    return preview
