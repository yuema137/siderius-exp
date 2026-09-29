"""Task-owned frequency-group holdout; original HDF5 indices are preserved."""

from __future__ import annotations

import hashlib
import importlib.util
import math
import random
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrequencyRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    family: Literal["training", "validation"]
    file: int = Field(ge=0, le=3)
    segment: int = Field(ge=0, lt=200)
    frequency_hz: int = Field(gt=0, lt=5_000_000)
    observed_peak_hz: int | None = Field(default=None, gt=0, lt=5_000_000)


class FrequencyCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["tidmad-frequency-catalog-v1"] = "tidmad-frequency-catalog-v1"
    source_sha256: dict[str, str]
    rows: tuple[FrequencyRow, ...]

    @model_validator(mode="after")
    def complete(self):
        expected = {
            (f, i, s)
            for f in ("training", "validation")
            for i in range(4)
            for s in range(200)
        }
        keys = [(r.family, r.file, r.segment) for r in self.rows]
        if len(keys) != len(set(keys)) or set(keys) != expected:
            raise ValueError(
                "catalog must identify every original segment of both families in band 0-3 exactly once"
            )
        names = {
            f"abra_{f}_{i:04d}.h5" for f in ("training", "validation") for i in range(4)
        }
        if set(self.source_sha256) != names or any(
            len(v) != 64 or any(c not in "0123456789abcdef" for c in v)
            for v in self.source_sha256.values()
        ):
            raise ValueError("catalog requires SHA256 of all eight original files")
        return self


class FrequencySplit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["tidmad-frequency-split-v1"] = "tidmad-frequency-split-v1"
    catalog: FrequencyCatalog
    train_hz: tuple[int, ...]
    validation_hz: tuple[int, ...]
    test_hz: tuple[int, ...]
    seed: int = 42

    @model_validator(mode="after")
    def partition(self):
        values = (self.train_hz, self.validation_hz, self.test_hz)
        groups = [set(value) for value in values]
        if any(
            len(value) != len(group)
            for value, group in zip(values, groups, strict=True)
        ):
            raise ValueError("frequency groups must not repeat a label")
        if any(not g for g in groups) or any(
            groups[i] & groups[j] for i in range(3) for j in range(i)
        ):
            raise ValueError(
                "train, validation and final-test frequency groups must be nonempty and disjoint"
            )
        if set.union(*groups) != {r.frequency_hz for r in self.catalog.rows}:
            raise ValueError("every catalog frequency must belong to exactly one group")
        for name in ("train", "validation", "test"):
            if any(not v for v in self.population(name).values()):
                raise ValueError(
                    f"{name} must retain at least one segment in every band file; choose another frequency partition"
                )
        return self

    def population(self, split: str) -> dict[int, list[int]]:
        if split not in ("train", "validation", "test"):
            raise ValueError("unknown split")
        frequencies = set(getattr(self, f"{split}_hz"))
        family = "training" if split == "train" else "validation"
        return {
            i: sorted(
                r.segment
                for r in self.catalog.rows
                if r.family == family and r.file == i and r.frequency_hz in frequencies
            )
            for i in range(4)
        }


def make_split(
    catalog: FrequencyCatalog,
    *,
    validation_fraction: float = 0.2,
    test_fraction: float = 0.2,
    seed: int = 42,
) -> FrequencySplit:
    if not (
        0 < validation_fraction < 1
        and 0 < test_fraction < 1
        and validation_fraction + test_fraction < 1
    ):
        raise ValueError("leave positive frequency fractions for all three sets")
    frequencies = sorted({r.frequency_hz for r in catalog.rows})
    random.Random(seed).shuffle(frequencies)
    nv, nt = (
        math.ceil(len(frequencies) * validation_fraction),
        math.ceil(len(frequencies) * test_fraction),
    )
    return FrequencySplit(
        catalog=catalog,
        validation_hz=tuple(sorted(frequencies[:nv])),
        test_hz=tuple(sorted(frequencies[nv : nv + nt])),
        train_hz=tuple(sorted(frequencies[nv + nt :])),
        seed=seed,
    )


def sample_population(
    population: dict[int, list[int]], portion: float, seed: int
) -> dict[int, list[int]]:
    if not 0 < portion <= 1:
        raise ValueError("portion must be in (0, 1]")
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
        "_tidmad_frequency_base_" + hashlib.sha256(str(path).encode()).hexdigest()[:12]
    )
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


class FrequencySplitDataPath(_base().TidmadTaskDataPath):
    """Ordinary scope capability, deliberately not a frozen-pool capability."""

    task_data_path_id = "tidmad_frequency_split"

    def __init__(self, split: dict):
        self.split = FrequencySplit.model_validate(split)

    def _frequency_scope(self, request, leg):
        if (
            request.subset_ref != "0-3"
            or request.selection_strategy != "snapshot"
            or request.target_partitions
        ):
            raise ValueError(
                "frequency tutorial requires snapshot selection over band 0-3"
            )
        if request.task_parameters.get("seg_size") != 40000:
            raise ValueError("frequency tutorial retains the 40000-sample model window")
        seed = self.split.seed if request.seed is None else request.seed
        return _base().TidmadScope(
            sample_set=sample_population(
                self.split.population(leg), request.portion, seed
            ),
            seg_size=40000,
            profile=_base().resolve_dataset_profile(),
        )

    def build_training_scope(self, request):
        return self._frequency_scope(request, "train")

    def build_eval_scope(self, request):
        return self._frequency_scope(request, "validation")

    def build_final_test_scope(self):
        """Explicit post-selection scope; never used by workflow evaluation."""
        return _base().TidmadScope(
            sample_set=self.split.population("test"),
            seg_size=40000,
            profile=_base().resolve_dataset_profile(),
        )
