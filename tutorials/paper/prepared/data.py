"""Create a small, independently identified task/data pair from real observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Literal

import h5py
import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tasks.shared.prepared_regression import PreparedDeclaration
from tutorials.paper.prepared.http_ranges import HTTPRangeReader
from tutorials.paper.runner import ROOT, disjoint

Task = Literal["project8", "ligo"]
SOURCES = Path(__file__).with_name("sources.json")


class DatasetRecipe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    task: Task
    name: str = Field(default="demo-001", pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,60}$")
    train_rows: int = Field(default=512, ge=20, le=2000)
    validation_rows: int = Field(default=1000, ge=20, le=1000)
    seed: int = Field(default=42, ge=0)
    resplit_validation_fraction: float | None = Field(default=None, ge=0.1, le=0.9)

    @model_validator(mode="after")
    def loss_subset_size(self):
        if self.validation_rows % 10:
            raise ValueError(
                "validation_rows must be a multiple of 10 for the fixed 10% loss subset"
            )
        return self


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def _read_prepared(
    recipe: DatasetRecipe, source: Path, *, source_task: Path | None = None
):
    """Read only selected rows; verify the source declaration, not every raw byte."""
    declaration_path = (
        source_task / "declared/prepared.json"
        if source_task
        else ROOT / f"tasks/phyts_{recipe.task}/declared/prepared.json"
    )
    declaration = PreparedDeclaration.model_validate_json(declaration_path.read_text())
    source_manifest = json.loads((source / "manifest.json").read_text())
    if sha(source / "manifest.json") != declaration.manifest_sha256:
        raise ValueError(
            "source is not the pinned prepared dataset; use its original manifest or the download route"
        )
    arrays, identities = {}, {}
    for split, count, directory in [
        ("train", recipe.train_rows, "training"),
        ("validation", recipe.validation_rows, "evaluator/validation"),
    ]:
        x = np.load(
            source / directory / "inputs.npy", mmap_mode="r", allow_pickle=False
        )
        y = np.load(
            source / directory / "targets.npy", mmap_mode="r", allow_pickle=False
        )
        expected = (
            declaration.train_count
            if split == "train"
            else declaration.validation_count
        )
        if x.shape != (
            expected,
            declaration.channels,
            declaration.length,
        ) or y.shape != (expected, 1):
            raise ValueError(
                "prepared source shapes differ from the pinned declaration"
            )
        if x.dtype != np.float32 or y.dtype != np.float32:
            raise ValueError("prepared source must contain float32 arrays")
        if count > expected:
            raise ValueError(
                "requested rows exceed this source split; reduce the recipe counts"
            )
        arrays[split] = (x[:count].copy(), y[:count].copy())
        identities[split] = (
            source_manifest["row_identities"][split][:count]
            if source_task
            else [f"{split}:{i}" for i in range(count)]
        )
    return (
        arrays,
        identities,
        {
            "mode": "existing",
            "source_manifest_sha256": declaration.manifest_sha256,
            "integrity_scope": "Pinned source manifest and array metadata; selected output bytes hashed. Full source arrays were not rehashed.",
        },
    )


def _read_remote(recipe: DatasetRecipe):
    catalog = json.loads(SOURCES.read_text())
    arrays, identities, transfers = {}, {}, []
    for split, count, raw_split in [
        ("train", recipe.train_rows, "train"),
        (
            "validation",
            recipe.validation_rows,
            "valid" if recipe.task == "project8" else "val",
        ),
    ]:
        xs, ys, remaining = [], [], count
        for entry in catalog["files"][recipe.task]:
            if entry["path"].split("/")[1] != raw_split or remaining == 0:
                continue
            url = f"https://huggingface.co/datasets/{catalog['repository']}/resolve/{catalog['revision']}/{entry['path']}"
            with HTTPRangeReader(url, entry["bytes"]) as stream:
                with h5py.File(stream, "r") as raw:
                    target = "energy_eV" if recipe.task == "project8" else "chirp_mass"
                    take = min(remaining, len(raw[target]))
                    y = np.asarray(raw[target][:take], dtype=np.float32).reshape(-1, 1)
                    if recipe.task == "project8":
                        channels = []
                        for channel in ("I", "Q"):
                            values = raw[f"output_ts_{channel}"][:take].astype(
                                np.float64
                            )
                            values += raw[f"output_ts_{channel}_cav_noise"][:take]
                            std = values.std(axis=-1, keepdims=True)
                            channels.append(
                                (values - values.mean(axis=-1, keepdims=True))
                                / np.where(std > 0, std, 1)
                            )
                        x = np.stack(channels, axis=1).astype(np.float32)
                    else:
                        x = np.asarray(
                            raw["whitened_injected"][:take, :, 15104:16128],
                            dtype=np.float32,
                        )
                transfers.append(
                    {
                        **entry,
                        "selected_rows": take,
                        "transferred_bytes": stream.downloaded_bytes,
                    }
                )
            xs.append(x)
            ys.append(y)
            remaining -= take
        if remaining:
            raise ValueError("requested row count exceeds the small source catalog")
        arrays[split] = (np.concatenate(xs), np.concatenate(ys))
        identities[split] = [f"{split}:{i}" for i in range(count)]
    return (
        arrays,
        identities,
        {
            "mode": "download",
            "repository": catalog["repository"],
            "revision": catalog["revision"],
            "files": transfers,
            "integrity_scope": "Exact HTTPS ranges at a pinned release revision; output arrays hashed. Release whole-file hashes are recorded, not verified by partial reads.",
        },
    )


def prepare(
    project: Path, recipe: DatasetRecipe, *, source: Path | None = None
) -> Path:
    """Write a new task/data pair; never overwrite a prior split or source array."""
    project = project.resolve()
    binding = json.loads((project / "project.json").read_text())
    infra = Path(binding["infra_checkout"])
    if any(not disjoint(project, p) for p in (ROOT, infra)):
        raise ValueError("use an initialized external project")
    destination = project / "data" / recipe.name
    task = project / "tasks" / f"{recipe.task}-{recipe.name}"
    if destination.exists() or task.exists():
        raise ValueError(
            "dataset name already exists; choose a new name to preserve prior inputs and results"
        )
    arrays, identities, provenance = (
        _read_prepared(
            recipe,
            source.resolve(),
            source_task=(project / "tasks" / f"{recipe.task}-{source.name}")
            if source.resolve().parent == project / "data"
            else None,
        )
        if source
        else _read_remote(recipe)
    )
    if recipe.task == "project8":
        from tasks.phyts_project8.dual_representation import (
            TRANSFORM_ID,
            dual_representation,
        )

        arrays = {
            split: (dual_representation(x) if x.shape[1] == 2 else x, y)
            for split, (x, y) in arrays.items()
        }
        provenance["input_transform"] = TRANSFORM_ID
    if recipe.resplit_validation_fraction is not None:
        x = np.concatenate([arrays[s][0] for s in ("train", "validation")])
        y = np.concatenate([arrays[s][1] for s in ("train", "validation")])
        ids = np.array(identities["train"] + identities["validation"])
        order = np.random.default_rng(recipe.seed).permutation(len(x))
        nval = max(20, int(len(x) * recipe.resplit_validation_fraction) // 10 * 10)
        for split, rows in (("validation", order[:nval]), ("train", order[nval:])):
            rows = np.sort(rows)
            arrays[split] = (x[rows], y[rows])
            identities[split] = ids[rows].tolist()
    for x, y in arrays.values():
        if (
            not np.isfinite(x).all()
            or not np.isfinite(y).all()
            or np.var(y.astype(np.float64)) <= 0
        ):
            raise ValueError(
                "selected inputs/targets must be finite and targets must vary"
            )
    destination.mkdir(parents=True)
    for split, directory in (
        ("train", "training"),
        ("validation", "evaluator/validation"),
    ):
        folder = destination / directory
        folder.mkdir(parents=True)
        x, y = arrays[split]
        np.save(folder / "inputs.npy", x, allow_pickle=False)
        np.save(folder / "targets.npy", y, allow_pickle=False)
    nval = len(arrays["validation"][0])
    loss = np.sort(
        np.random.default_rng(recipe.seed).choice(nval, nval // 10, replace=False)
    ).astype(np.int64)
    np.save(
        destination / "evaluator/validation/loss_indices.npy", loss, allow_pickle=False
    )
    artifacts = [
        {
            "path": str(p.relative_to(destination)),
            "bytes": p.stat().st_size,
            "sha256": sha(p),
        }
        for p in sorted(destination.rglob("*.npy"))
    ]
    dump(
        destination / "manifest.json",
        {
            "kind": "workflow-demo-only",
            "recipe": recipe.model_dump(),
            "provenance": provenance,
            "row_identities": identities,
            "artifacts": artifacts,
        },
    )
    shutil.copytree(
        ROOT / f"tasks/phyts_{recipe.task}",
        task,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
            "dual_representation",
            "tools",
            "DUAL_REPRESENTATION.md",
            "dual_representation.py",
        ),
    )
    if recipe.task == "project8":
        original = ROOT / "tasks/phyts_project8"
        for name in ("task_config.yaml", "dataset_profile.json"):
            shutil.copyfile(
                original / "declared/dual_representation" / name,
                task / "declared" / name,
            )
        composition = (original / "compositions/dual_representation.yaml").read_text()
        (task / "compositions/regression.yaml").write_text(
            composition.replace("../declared/dual_representation/", "../declared/")
        )
    (task / "compositions/dual_representation.yaml").unlink(missing_ok=True)
    declaration = PreparedDeclaration(
        task_id="phyts_project8_energy_dual"
        if recipe.task == "project8"
        else "phyts_ligo_chirp_mass",
        manifest_sha256=sha(destination / "manifest.json"),
        train_count=len(arrays["train"][0]),
        validation_count=nval,
        channels=arrays["train"][0].shape[1],
        length=arrays["train"][0].shape[-1],
        loss_indices=tuple(map(int, loss)),
    )
    (task / "declared/prepared.json").write_text(
        declaration.model_dump_json(indent=2) + "\n"
    )
    profile_path = task / "declared/dataset_profile.json"
    profile = json.loads(profile_path.read_text())
    profile["topology"]["populations"] = {
        "train": declaration.train_count,
        "validation": nval,
    }
    dump(profile_path, profile)
    description_path = task / "declared/task_config.yaml"
    config = yaml.safe_load(description_path.read_text())
    description = config["task_description"]
    if recipe.task == "ligo":
        description = description.split("\n")[0]
    description = description.replace(
        "Original train/validation split and row order are preserved; test data are absent.",
        "The demo manifest owns row membership; test data are absent.",
    )
    description = description.replace(
        "final Formal scoring uses all validation examples.",
        "Formal scoring uses the experiment-selected validation fraction.",
    )
    config["task_description"] = description + (
        f"\nThis is a small workflow demo, not the paper artifact: {declaration.train_count} training and {nval} validation events. "
        "Predict physical-unit targets. Primary metric is global validation R2 (higher is better); RMSE is secondary. "
        "Trial/Formal fractions select within these declared populations. Epoch-loss validation uses the fixed 10% subset. "
        "The validation score feeds back to the search agent; it is not an unseen final test. No test split is used."
    )
    description_path.write_text(yaml.safe_dump(config, sort_keys=False))
    (task / "README.md").write_text(
        "# User-owned workflow demo task\n\nOpen `compositions/regression.yaml` for the task entry, `declared/prepared.json` for counts and data identity, and the paired data directory's `manifest.json` for exact row membership and provenance. This is a small demo, not a paper artifact. Rebuild a new task/data pair to change a split; do not hand-edit counts or hashes.\n"
    )
    for path in destination.rglob("*.npy"):
        path.chmod(0o444)
    print(
        f"Saved task: {task}\nSaved data: {destination}\nRows: {declaration.train_count} train / {nval} validation / {len(loss)} epoch-loss validation"
    )
    return task / "compositions/regression.yaml"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--task", choices=("project8", "ligo"), required=True)
    parser.add_argument("--name", default="demo-001")
    parser.add_argument("--train-rows", type=int, default=512)
    parser.add_argument("--validation-rows", type=int, default=1000)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if (args.source is None) == (not args.download):
        parser.error("choose exactly one of --source PREPARED_DIRECTORY or --download")
    prepare(
        args.project,
        DatasetRecipe(
            task=args.task,
            name=args.name,
            train_rows=args.train_rows,
            validation_rows=args.validation_rows,
        ),
        source=args.source,
    )


if __name__ == "__main__":
    main()
