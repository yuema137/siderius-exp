"""Per-epoch validation is the one place the caller reaches across.

It submits a scope; the evaluator, which owns truth, returns admitted loss
observations. So what arrives is checked before it is honoured.

Each case names a defect nothing else would catch:

* ``test_a_caller_built_scope_is_admitted`` — the boundary has to let the
  legitimate request through. A refusal that rejects everything is not
  secure, it is broken, and it would fail deep inside a training run.
* ``test_a_scope_carrying_targets_is_refused`` — the attack the check
  exists for. `deserialize_scope` rebuilds the pack's BASE scope, so the
  refusing subclass does not survive the round trip; the check has to be on
  values, and a type-based one would pass here while admitting the forgery.
* ``test_a_training_split_scope_is_refused`` — training targets are
  supervision the caller already holds. Evaluating on them would score a
  model against its own training data and report it as validation.
* ``test_a_scope_naming_unknown_curves_is_refused`` — a scope may only name
  curves the evaluated population contains.
* ``test_the_admitted_scope_carries_the_evaluators_targets`` — the defect
  the first port shipped: the admitted payload re-serialized the caller's
  rows, whose targets are NaN, and `_TessCurveDataset` reads targets FROM
  THE SCOPE, so every per-epoch validation loss would have been NaN. The
  admitted scope must carry the manifest's targets, in the caller's order.
* ``test_a_curve_the_evaluator_cannot_measure_is_refused`` — an agent view
  that declares a curve the identity manifest lacks means the two views
  drifted apart; admission must say so rather than serve a partial scope.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from execute_tools.task_data_path import ScopeBuildRequest

from experiments.phyts_tess.main_orchestrator.public_data_path import (
    PublicTessTaskDataPath,
)
from experiments.phyts_tess.main_orchestrator.validation_scope import (
    admit_validation_scope,
)
from tasks.phyts_tess.runtime.tess_data_path import TessRow, TessScope

IDENTITY = ("split", "gaia_id", "tic", "sector")


@pytest.fixture
def view(tmp_path) -> Path:
    agent = tmp_path / "agent" / "manifests"
    agent.mkdir(parents=True)
    with (agent / "train.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*IDENTITY, "frot", "frot_err"])
        writer.writeheader()
        for index in range(4):
            writer.writerow(
                {
                    "split": "train",
                    "gaia_id": str(100 + index),
                    "tic": str(900 + index),
                    "sector": "20",
                    "frot": f"{0.5 + index / 10:.4f}",
                    "frot_err": "0.01",
                }
            )
    with (agent / "predict.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(IDENTITY))
        writer.writeheader()
        for index in range(3):
            writer.writerow(
                {
                    "split": "val",
                    "gaia_id": str(200 + index),
                    "tic": str(800 + index),
                    "sector": "21",
                }
            )
    return agent.parent


VAL_TRUTH = {f"{200 + index}:21": 1.5 + index / 10 for index in range(3)}


@pytest.fixture
def truth(tmp_path) -> Path:
    """The evaluator's identity manifest: the same population, with targets."""
    manifest = tmp_path / "evaluator" / "manifests" / "rotation_identity.csv"
    manifest.parent.mkdir(parents=True)
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*IDENTITY, "frot", "frot_err"])
        writer.writeheader()
        for index in range(4):
            writer.writerow(
                {
                    "split": "train",
                    "gaia_id": str(100 + index),
                    "tic": str(900 + index),
                    "sector": "20",
                    "frot": f"{0.5 + index / 10:.4f}",
                    "frot_err": "0.01",
                }
            )
        for key, frot in VAL_TRUTH.items():
            gaia_id, sector = key.split(":")
            writer.writerow(
                {
                    "split": "val",
                    "gaia_id": gaia_id,
                    "tic": str(600 + int(gaia_id)),
                    "sector": sector,
                    "frot": f"{frot:.4f}",
                    "frot_err": "0.02",
                }
            )
    return manifest


def _request(portion: float = 1.0) -> ScopeBuildRequest:
    return ScopeBuildRequest(
        round_kind="formal", selection_strategy="snapshot", portion=portion, seed=0
    )


def test_a_caller_built_scope_is_admitted(view, truth):
    task = PublicTessTaskDataPath(agent_view=str(view))
    scope = task.build_eval_scope(_request())

    admitted = admit_validation_scope(
        task.serialize_scope(scope), agent_view=view, truth_manifest=truth
    )
    assert admitted.rows == len(scope.rows)
    # Rebuilt by the admitting side, so what the evaluator honours is what it
    # validated — the same identities — rather than the bytes it was handed.
    served = task.deserialize_scope(admitted.payload)
    assert isinstance(served, TessScope)
    assert served.keys == scope.keys and served.split == "val"


def test_a_scope_carrying_targets_is_refused(view, truth):
    """The forgery a type check would miss."""
    task = PublicTessTaskDataPath(agent_view=str(view))
    scope = task.build_eval_scope(_request())
    forged = TessScope(
        split="val",
        rows=tuple(
            TessRow(gaia_id=row.gaia_id, sector=row.sector, frot=1.234)
            for row in scope.rows
        ),
        sequence_length=scope.sequence_length,
    )

    with pytest.raises(ValueError, match="carries targets"):
        admit_validation_scope(
            task.serialize_scope(forged), agent_view=view, truth_manifest=truth
        )


def test_a_training_split_scope_is_refused(view, truth):
    task = PublicTessTaskDataPath(agent_view=str(view))
    training = task.build_training_scope(_request())

    with pytest.raises(ValueError, match="only 'val' may be evaluated"):
        admit_validation_scope(
            task.serialize_scope(training), agent_view=view, truth_manifest=truth
        )


def test_a_scope_naming_unknown_curves_is_refused(view, truth):
    task = PublicTessTaskDataPath(agent_view=str(view))
    scope = task.build_eval_scope(_request())
    intruder = TessScope(
        split="val",
        rows=(*scope.rows, TessRow(gaia_id=999, sector=99, frot=float("nan"))),
        sequence_length=scope.sequence_length,
    )

    with pytest.raises(ValueError, match="outside the evaluated population"):
        admit_validation_scope(
            task.serialize_scope(intruder), agent_view=view, truth_manifest=truth
        )


def test_the_admitted_scope_carries_the_evaluators_targets(view, truth):
    task = PublicTessTaskDataPath(agent_view=str(view))
    scope = task.build_eval_scope(_request())
    keys = list(scope.keys)
    keys.reverse()  # the caller's order, not the manifest's, must be preserved
    submitted = TessScope(
        split="val",
        rows=tuple(row for key in keys for row in scope.rows if row.key == key),
    )

    admitted = admit_validation_scope(
        task.serialize_scope(submitted), agent_view=view, truth_manifest=truth
    )

    served = task.deserialize_scope(admitted.payload)
    assert isinstance(served, TessScope)
    assert [row.key for row in served.rows] == keys
    assert [row.frot for row in served.rows] == pytest.approx(
        [VAL_TRUTH[key] for key in keys]
    ), "per-epoch validation is computed against these; NaN here is NaN loss"
    assert admitted.rows == 3


def test_a_curve_the_evaluator_cannot_measure_is_refused(view, truth):
    lines = truth.read_text(encoding="utf-8").splitlines(keepends=True)
    truth.write_text("".join(line for line in lines if not line.startswith("val,202,")))
    task = PublicTessTaskDataPath(agent_view=str(view))
    scope = task.build_eval_scope(_request())

    with pytest.raises(ValueError, match="carries no target for curves"):
        admit_validation_scope(
            task.serialize_scope(scope), agent_view=view, truth_manifest=truth
        )
