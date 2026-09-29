"""Task-owned file-index holdout for a single TIDMAD band."""

from __future__ import annotations

import hashlib
import importlib.util
import math
import random
import sys
from pathlib import Path
from typing import Literal

from execute_tools.task_data_path import ScopeBuildRequest
from pydantic import BaseModel, ConfigDict, model_validator


class FileSplit(BaseModel):
    """Different file indices represent the tutorial's held-out frequency ranges.

    This declares file-level separation, not exact frequency-label separation.
    Every original segment is retained within its assigned file population.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    train_files: tuple[int, ...] = (0, 1)
    validation_files: tuple[int, ...] = (2,)
    test_files: tuple[int, ...] = (3,)
    seed: int = 42

    @model_validator(mode="after")
    def partition(self):
        values = (self.train_files, self.validation_files, self.test_files)
        groups = [set(value) for value in values]
        if any(
            not group or len(value) != len(group)
            for value, group in zip(values, groups, strict=True)
        ):
            raise ValueError(
                "each file group must be nonempty with no repeated indices"
            )
        if any(groups[i] & groups[j] for i in range(3) for j in range(i)):
            raise ValueError(
                "training, validation and final-test file indices must be disjoint"
            )
        if set.union(*groups) != set(range(4)):
            raise ValueError(
                "this one-band tutorial partitions exactly file indices 0,1,2,3"
            )
        return self

    def population(
        self, split: Literal["train", "validation", "test"]
    ) -> dict[int, list[int]]:
        if split not in ("train", "validation", "test"):
            raise ValueError("unknown split")
        return {i: list(range(200)) for i in sorted(getattr(self, f"{split}_files"))}


def sample_population(
    population: dict[int, list[int]], portion: float, seed: int
) -> dict[int, list[int]]:
    if not 0 < portion <= 1:
        raise ValueError("portion must be in (0,1]")
    return {
        i: sorted(
            random.Random(f"{seed}:{i}").sample(
                rows, max(1, math.ceil(len(rows) * portion))
            )
        )
        for i, rows in population.items()
    }


def _base():
    path = Path(__file__).with_name("tidmad_data_path.py")
    name = (
        "_tidmad_file_split_base_" + hashlib.sha256(str(path).encode()).hexdigest()[:12]
    )
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"missing TIDMAD base adapter: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


class FileSplitDataPath(_base().TidmadTaskDataPath):
    """Ordinary per-file scopes, without the paper frozen-pool capability."""

    task_data_path_id = "tidmad_file_split"

    def __init__(self, split: dict):
        self.split = FileSplit.model_validate(split)

    def _file_scope(
        self, request: ScopeBuildRequest, leg: Literal["train", "validation"]
    ):
        if (
            request.subset_ref != "0-3"
            or request.selection_strategy != "snapshot"
            or request.target_partitions
        ):
            raise ValueError(
                "file-split tutorial requires snapshot selection over band 0-3"
            )
        if request.task_parameters.get("seg_size") != 40000:
            raise ValueError(
                "file-split tutorial retains the 40000-sample model window"
            )
        seed = self.split.seed if request.seed is None else request.seed
        return _base().TidmadScope(
            sample_set=sample_population(
                self.split.population(leg), request.portion, seed
            ),
            seg_size=40000,
            profile=_base().resolve_dataset_profile(),
        )

    def build_training_scope(self, request: ScopeBuildRequest):
        return self._file_scope(request, "train")

    def build_eval_scope(self, request: ScopeBuildRequest):
        return self._file_scope(request, "validation")

    def build_final_test_scope(self):
        """Post-selection only; the workflow never requests this scope."""
        return _base().TidmadScope(
            sample_set=self.split.population("test"),
            seg_size=40000,
            profile=_base().resolve_dataset_profile(),
        )
