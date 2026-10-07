"""Inspect declared image splits and save a separate, explicit resplit task."""

from __future__ import annotations

import hashlib
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from tasks.oxford_iiit_pet.tools.oxford_iiit_pet import (
    ManifestRow,
    parse_manifest_csv,
    render_manifest_csv,
)
from tutorials.shared.runtime import ROOT, disjoint


class SplitReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    manifest: Path
    sha256: str
    count: int
    per_class: dict[int, int]


def split_paths(composition: Path) -> dict[str, Path]:
    """Resolve explicit task-owned manifests; never fall back to training for eval."""
    task = composition.parent.parent.resolve()
    payload = yaml.safe_load(composition.read_text())
    config = payload["task_data_path"]["config"]
    paths = {
        "train": (composition.parent / config["manifest_path"]["ref"]).resolve(),
        "validation": (
            composition.parent / config["eval_manifest_path"]["ref"]
        ).resolve(),
        "final": task / "data/manifests/gate2_final.csv",
    }
    if any(not p.is_relative_to(task) for p in paths.values()):
        raise ValueError(
            "Pet split manifests must remain inside the copied task package"
        )
    return paths


def read_splits(composition: Path) -> dict[str, tuple[ManifestRow, ...]]:
    splits = {
        role: tuple(parse_manifest_csv(p.read_text()))
        for role, p in split_paths(composition).items()
    }
    seen: set[str] = set()
    for role, rows in splits.items():
        ids = {r.image_id for r in rows}
        if not rows or len(ids) != len(rows) or seen & ids:
            raise ValueError(
                f"{role}: empty split, duplicate IDs or train/validation/final overlap"
            )
        if {r.class_index for r in rows} != set(range(37)):
            raise ValueError(f"{role}: every one of the 37 classes must be represented")
        for row in rows:
            if row.scope != role or row.official_class_id != row.class_index + 1:
                raise ValueError(f"{role}: inconsistent scope or class label")
            if Path(row.image_id).name != row.image_id or row.image_id in {".", ".."}:
                raise ValueError("image_id must be a filename stem, not a path")
        seen.update(ids)
    return splits


def inspect_data(
    composition: Path, images: Path, *, decode: bool = False
) -> dict[str, SplitReport]:
    """Check every declared image; decode only search images, never final pixels."""
    from PIL import Image

    splits = read_splits(composition)
    reports = {}
    paths = split_paths(composition)
    for role, rows in splits.items():
        for row in rows:
            path = images / f"{row.image_id}.jpg"
            if not path.is_file():
                raise ValueError(
                    f"Missing image: {path}. Set data_dir to the existing images directory, or run the explicit download step."
                )
            if decode and role != "final":
                try:
                    with Image.open(path) as image:
                        image.convert("RGB").load()
                except (OSError, ValueError):
                    raise ValueError(
                        f"Unreadable JPEG: {path}. Restore this image before launching."
                    ) from None
        reports[role] = SplitReport(
            manifest=paths[role],
            sha256=hashlib.sha256(paths[role].read_bytes()).hexdigest(),
            count=len(rows),
            per_class=dict(sorted(Counter(r.class_index for r in rows).items())),
        )
    return reports


def resplit_task(
    composition: Path, destination: Path, *, validation_per_class: int, seed: int
) -> Path:
    """Seeded, stratified split of the old train+validation pool into a new task.

    Final membership and bytes remain frozen. Existing tasks are never overwritten.
    """
    source = composition.parent.parent.resolve()
    destination = destination.resolve()
    if not disjoint(destination, ROOT) or not disjoint(destination, source):
        raise ValueError(
            "new task must be outside the repository and separate from the original task"
        )
    if destination.exists():
        raise ValueError(
            "choose a new task directory; resplitting never overwrites a task"
        )
    splits = read_splits(composition)
    pool: dict[int, list[ManifestRow]] = defaultdict(list)
    for row in (*splits["train"], *splits["validation"]):
        pool[row.class_index].append(row)
    if not 1 <= validation_per_class < min(map(len, pool.values())):
        raise ValueError(
            "leave at least one training and one validation image per class"
        )
    rng = random.Random(seed)
    selected: dict[str, list[ManifestRow]] = {"train": [], "validation": []}
    for rows in sorted(pool.values(), key=lambda rows: rows[0].class_index):
        rows.sort(key=lambda r: r.image_id)
        rng.shuffle(rows)
        for i, row in enumerate(rows):
            role = "validation" if i < validation_per_class else "train"
            selected[role].append(
                ManifestRow.model_validate({**row.model_dump(), "scope": role})
            )
    shutil.copytree(
        source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    for role, rows in selected.items():
        (destination / f"data/manifests/tutorial_{role}.csv").write_text(
            render_manifest_csv(
                tuple(sorted(rows, key=lambda r: (r.class_index, r.image_id)))
            )
        )
    payload = yaml.safe_load(composition.read_text())
    config = payload["task_data_path"]["config"]
    config["manifest_path"] = {"ref": "../data/manifests/tutorial_train.csv"}
    config["eval_manifest_path"] = {"ref": "../data/manifests/tutorial_validation.csv"}
    old_profile = (composition.parent / payload["dataset_profile"]["config"]).resolve()
    profile = json.loads(old_profile.read_text())
    profile["partition_count"] = len(selected["train"])
    profile["topology"]["scope_authority"] = "data/manifests/tutorial_train.csv"
    (destination / "declared/tutorial_profile.json").write_text(
        json.dumps(profile, indent=2)
    )
    payload["dataset_profile"]["config"] = "../declared/tutorial_profile.json"
    new_composition = destination / "compositions/tutorial_split.yaml"
    new_composition.write_text(yaml.safe_dump(payload, sort_keys=False))
    (destination / "data/tutorial_split.json").write_text(
        json.dumps(
            {
                "seed": seed,
                "validation_per_class": validation_per_class,
                "source_composition": str(composition),
                "source_manifests": {
                    role: hashlib.sha256(path.read_bytes()).hexdigest()
                    for role, path in split_paths(composition).items()
                },
            },
            indent=2,
        )
    )
    return new_composition
