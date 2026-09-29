"""The orchestration boundary, made executable.

Each case names a defect nothing else would catch:

* ``test_the_evaluated_scope_refuses_to_produce_truth`` — the boundary
  itself. Drop the override and the public scope inherits the pack's
  ``truth()``, which reads ``row.frot``; every other test still passes and
  an external caller silently gains the answers.
* ``test_training_supervision_still_works`` — the other half. A boundary
  that also blocks supervision is not a boundary, it is a broken task, and
  it would fail far away from here with an unhelpful message.
* ``test_a_view_carrying_evaluated_targets_is_refused`` — the published
  view is built by a separate tool. If a future change to that tool leaks a
  target column, this path must refuse rather than serve it.
* ``test_the_public_path_restates_no_preprocessing`` — the frozen task
  definition must be inherited, not copied. A second normalization is a
  second thing to get wrong, and it would drift silently because both
  copies would look correct in isolation.
"""

from __future__ import annotations

import csv
import inspect
import math
from pathlib import Path

import pytest
from execute_tools.task_data_path import ScopeBuildRequest

from experiments.phyts_tess.main_orchestrator import public_data_path as module
from experiments.phyts_tess.main_orchestrator.public_data_path import (
    PublicTessScope,
    PublicTessTaskDataPath,
)
from tasks.phyts_tess.runtime.tess_data_path import (
    PhytsTessTaskDataPath,
    ValidationScopeError,
)

IDENTITY = ("split", "gaia_id", "tic", "sector")


def _request(portion: float = 1.0) -> ScopeBuildRequest:
    return ScopeBuildRequest(
        round_kind="formal",
        selection_strategy="snapshot",
        portion=portion,
        seed=0,
    )


def _write(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in columns})


def _view(tmp_path: Path, *, evaluated_targets: bool = False) -> Path:
    """A minimal agent view, shaped exactly as build_views.py writes one."""
    agent = tmp_path / "agent"
    train = [
        {
            "split": "train",
            "gaia_id": str(100 + index),
            "tic": str(900 + index),
            "sector": "20",
            "frot": f"{0.5 + index / 10:.4f}",
            "frot_err": "0.01",
        }
        for index in range(4)
    ]
    evaluated = [
        {
            "split": "val",
            "gaia_id": str(200 + index),
            "tic": str(800 + index),
            "sector": "21",
            "frot": f"{1.5 + index / 10:.4f}",
            "frot_err": "0.02",
        }
        for index in range(3)
    ]
    _write(agent / "manifests" / "train.csv", train, [*IDENTITY, "frot", "frot_err"])
    _write(
        agent / "manifests" / "predict.csv",
        evaluated,
        [*IDENTITY, "frot"] if evaluated_targets else list(IDENTITY),
    )
    return agent


def test_the_evaluated_scope_refuses_to_produce_truth(tmp_path):
    """A refusal, not an empty mapping.

    An empty mapping would let a caller score every prediction as missing and
    still receive a number back.
    """
    path = PublicTessTaskDataPath(agent_view=str(_view(tmp_path)))
    scope = path.build_eval_scope(_request())

    assert isinstance(scope, PublicTessScope)
    assert len(scope.keys) == 3, "identities must survive; only targets are withheld"

    with pytest.raises(ValidationScopeError) as excinfo:
        scope.truth()
    assert module.EVALUATED_TRUTH_IS_EVALUATOR_OWNED in str(excinfo.value)

    # Defence in depth: even reconstructed as the pack's own scope type, the
    # rows carry nothing a metric could mistake for a measurement.
    assert all(math.isnan(row.frot) for row in scope.rows)


def test_training_supervision_still_works(tmp_path):
    """Training targets are supervision and must cross intact."""
    path = PublicTessTaskDataPath(agent_view=str(_view(tmp_path)))
    scope = path.build_training_scope(_request())

    truth = scope.truth()
    assert len(truth) == 4
    assert all(math.isfinite(value) for value in truth.values())
    assert scope.split == "train"


def test_a_view_carrying_evaluated_targets_is_refused(tmp_path):
    """The published view is built elsewhere; refuse a leaky one on read."""
    path = PublicTessTaskDataPath(
        agent_view=str(_view(tmp_path, evaluated_targets=True))
    )
    with pytest.raises(ValidationScopeError, match="not answer-free"):
        path.build_eval_scope(_request())


def test_an_incomplete_view_names_the_tool_that_builds_it(tmp_path):
    """A missing manifest must not surface as a bare FileNotFoundError."""
    (tmp_path / "agent" / "manifests").mkdir(parents=True)
    with pytest.raises(ValidationScopeError, match="build_views.py"):
        PublicTessTaskDataPath(agent_view=str(tmp_path / "agent"))


def test_the_public_path_restates_no_preprocessing():
    """The frozen task definition is inherited, never copied.

    Sequence length, the truncate/pad rule and the z-score order are the task
    definition. A second copy here would drift silently, because each copy
    would look correct on its own.
    """
    assert issubclass(PublicTessTaskDataPath, PhytsTessTaskDataPath)

    source = inspect.getsource(module)
    for frozen in ("def normalize_curve", "np.mean", "np.std", "SEQUENCE_LENGTH ="):
        assert frozen not in source, (
            f"{frozen!r} is restated in public_data_path.py; the frozen "
            "preprocessing belongs to the pack and must be inherited"
        )

    # Only the row SOURCE is overridden, plus the scope type that refuses.
    overridden = {
        name
        for name, value in vars(PublicTessTaskDataPath).items()
        if callable(value) and not name.startswith("__")
    }
    assert overridden == {"_rows", "build_eval_scope"}, (
        f"public path overrides {sorted(overridden)}; each addition is another "
        "place the task definition can diverge from the pack"
    )
