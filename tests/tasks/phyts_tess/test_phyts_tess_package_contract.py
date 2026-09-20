"""Task-owned PhyTS TESS rotation-regression contract checks.

Each case below names a defect that nothing else in this repository, no
static checker and no Pydantic declaration would catch:

* ``test_scopes_are_star_disjoint`` — the framework has no scope-aware
  checker by design, so split independence is this package's own proof
  obligation. Distinct row counts and distinct scope hashes are NOT evidence.
* ``test_a_star_admitted_to_both_scopes_is_detected`` — the required failing
  counterexample. Without it the disjointness assertion above could be
  passing vacuously.
* ``test_portion_draw_keeps_a_star_whole`` — a row-wise sub-portion draw
  would still be between-split clean and would still pass every other check
  here, while splitting one star's curves across a round's own train and
  eval draws.
* ``test_no_constructible_scope_names_the_test_split`` — the held-out
  population must be unreachable by construction, not merely unused.
* ``test_r2_and_rmse_match_hand_computed_values`` — the arithmetic. A sign
  error or a wrong denominator produces a plausible number that no type or
  schema can see.
* ``test_constant_mean_predictor_scores_exactly_zero`` — R-squared's
  defining property, and the one that fails first if the total sum of
  squares is ever taken over the wrong population.
* ``test_partial_deliverable_is_refused`` — silent imputation of a missing
  prediction would produce a real-looking score computed from something the
  model never said.
* ``test_scope_codec_round_trip_is_canonical`` — the framework HASHES the
  serialized scope to verify transport, so an unstable ordering breaks
  composed runs and nothing else reports it.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

EXP_ROOT = Path(__file__).resolve().parents[3]
PACK = EXP_ROOT / "tasks" / "phyts_tess"
MANIFEST = PACK / "data" / "manifests" / "rotation_identity.csv"
COMPOSITION = PACK / "compositions" / "rotation_regression.yaml"

#: Staged run data root. Declared, validated, and skipped-with-a-reason when
#: absent — never silently replaced by a developer-specific location.
DATA_DIR_ENV = "PHYTS_TESS_DATA_DIR"


def _load(name: str, relative: str):
    """Import a pack module by path, the way the framework loads it."""
    path = PACK / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"cannot load pack module {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def data_path_module():
    return _load("phyts_tess_data_path", "runtime/tess_data_path.py")


@pytest.fixture(scope="module")
def scoring_module():
    return _load("phyts_tess_scoring", "runtime/scoring.py")


@pytest.fixture(scope="module")
def data_path(data_path_module):
    return data_path_module.PhytsTessTaskDataPath(manifest_path=str(MANIFEST))


@pytest.fixture(scope="module")
def full_request():
    from execute_tools.task_data_path import ScopeBuildRequest

    return ScopeBuildRequest(
        round_kind="formal", selection_strategy="snapshot", portion=1.0, seed=20260920
    )


def _staged_data_dir() -> Path:
    configured = os.environ.get(DATA_DIR_ENV)
    if not configured:
        pytest.skip(
            f"{DATA_DIR_ENV} is not set. This case needs the staged run data root; "
            "create it with tasks/phyts_tess/tools/stage_data.py. Skipped means "
            "UNVERIFIED, not passed."
        )
    root = Path(configured).resolve()
    assert root.is_dir(), f"{DATA_DIR_ENV} does not name a directory: {root}"
    return root


# --------------------------------------------------------------- split evidence


def test_scopes_are_star_disjoint(data_path, full_request):
    """Obligation: independence at the identity level the task DECLARES.

    The forbidden overlap is the STAR (Gaia DR3 identifier), not the row:
    one star contributes several light curves, so comparing row keys would
    pass while the same object appeared on both sides.

    Population sizes are asserted independently BEFORE the intersection, so
    an empty set can never satisfy this vacuously.
    """
    train = data_path.build_training_scope(full_request)
    evaluation = data_path.build_eval_scope(full_request)

    assert len(train.rows) == 3338, (
        "training population changed from the pinned manifest"
    )
    assert len(evaluation.rows) == 442, (
        "evaluation population changed from the pinned manifest"
    )

    train_stars = {row.gaia_id for row in train.rows}
    eval_stars = {row.gaia_id for row in evaluation.rows}
    assert len(train_stars) == 505
    assert len(eval_stars) == 64
    assert not (train_stars & eval_stars)


def test_a_star_admitted_to_both_scopes_is_detected(data_path, full_request):
    """The required failing counterexample.

    Deliberately admit one held-out star to the training population and
    assert the SAME comparison now fails. Without this, the assertion above
    could be checking a property no construction can violate.
    """
    train = data_path.build_training_scope(full_request)
    evaluation = data_path.build_eval_scope(full_request)

    leaked = evaluation.rows[0]
    contaminated = {row.gaia_id for row in train.rows} | {leaked.gaia_id}
    eval_stars = {row.gaia_id for row in evaluation.rows}

    overlap = contaminated & eval_stars
    assert overlap == {leaked.gaia_id}, (
        "the disjointness check cannot see a planted star"
    )


def test_portion_draw_keeps_a_star_whole(data_path, data_path_module):
    """A sub-portion draw selects STARS, never individual light curves.

    Row-wise sampling would leave every between-split property intact and
    would pass every other case in this file, while putting some of a star's
    curves in a round's training draw and the rest in its evaluation draw.
    """
    from execute_tools.task_data_path import ScopeBuildRequest

    request = ScopeBuildRequest(
        round_kind="trial", selection_strategy="snapshot", portion=0.1, seed=20260920
    )
    drawn = data_path.build_training_scope(request)
    everything = data_path.build_training_scope(
        ScopeBuildRequest(
            round_kind="formal",
            selection_strategy="snapshot",
            portion=1.0,
            seed=20260920,
        )
    )

    assert 0 < len(drawn.rows) < len(everything.rows), (
        "portion=0.1 drew nothing or everything"
    )

    per_star_total: dict[int, int] = {}
    for row in everything.rows:
        per_star_total[row.gaia_id] = per_star_total.get(row.gaia_id, 0) + 1
    per_star_drawn: dict[int, int] = {}
    for row in drawn.rows:
        per_star_drawn[row.gaia_id] = per_star_drawn.get(row.gaia_id, 0) + 1

    partial = {
        star: (count, per_star_total[star])
        for star, count in per_star_drawn.items()
        if count != per_star_total[star]
    }
    assert not partial, f"these stars were split across the draw: {partial}"


def test_no_constructible_scope_names_the_test_split(data_path_module, data_path):
    """The held-out population is unreachable by construction, not by habit.

    Three independent routes are closed: the declared split type, the
    committed identity manifest, and scope deserialization.
    """
    import typing

    admitted = set(typing.get_args(data_path_module.TessSplit))
    assert admitted == {"train", "val"}, f"TessSplit admits {admitted}"

    rows = MANIFEST.read_text(encoding="utf-8").splitlines()
    declared_splits = {line.split(",", 1)[0] for line in rows[1:] if line}
    assert declared_splits == {"train", "val"}, declared_splits

    payload = json.dumps(
        {
            "kind": "phyts_tess_rotation_scope_v1",
            "scope": {
                "split": "test",
                "rows": [{"gaia_id": 1, "sector": 1, "frot": 1.0}],
                "sequence_length": 1024,
            },
        }
    )
    # Pydantic's ValidationError subclasses ValueError, so this is the
    # narrowest type that covers both the split rejection and a malformed
    # envelope without catching an unrelated crash.
    with pytest.raises(ValueError, match="split"):
        data_path.deserialize_scope(payload)


def test_scope_codec_round_trip_is_canonical(data_path, full_request):
    """The framework hashes this payload to verify scope transport.

    An unstable member ordering makes the same scope serialize to two
    different strings, which fails a composed child's digest check and is
    reported nowhere else.
    """
    scope = data_path.build_eval_scope(full_request)
    once = data_path.serialize_scope(scope)
    twice = data_path.serialize_scope(data_path.deserialize_scope(once))
    assert once == twice

    rebuilt = data_path.build_eval_scope(full_request)
    assert data_path.serialize_scope(rebuilt) == once, (
        "rebuilding the same request drifted"
    )


# -------------------------------------------------------------------- metrics


def _metric(scoring_module, cls, name: str):
    from execute_tools.evaluation_metric import MetricSpec

    raw = json.loads(
        (PACK / "declared" / f"metric_{name}.json").read_text(encoding="utf-8")
    )
    contract_module = _load("phyts_tess_scoreability", "runtime/scoreability.py")
    raw["scoreability"] = contract_module.TessRotationScoreabilityContract()
    return cls(MetricSpec.model_validate(raw))


class _FixedScope:
    """Two curves with hand-chosen targets; no data root is touched."""

    def truth(self):
        return {"a": 1.0, "b": 3.0}


def test_r2_and_rmse_match_hand_computed_values(scoring_module):
    """Targets [1, 3] and predictions [2, 3].

    By hand: mean 2, total sum of squares (1-2)^2 + (3-2)^2 = 2, residual
    sum of squares (2-1)^2 + (3-3)^2 = 1, so R-squared = 1 - 1/2 = 0.5 and
    RMSE = sqrt(1/2). Hardcoded, never read back from the implementation.
    """
    r2 = _metric(scoring_module, scoring_module.TessRotationR2Metric, "r2")
    value, per_sample, _ = r2._compute(
        {}, evaluation_payload={"a": 2.0, "b": 3.0}, task_scope=_FixedScope()
    )
    assert value == 0.5
    assert per_sample is None, "R-squared is not decomposable per sample"

    rmse = _metric(scoring_module, scoring_module.TessRotationRmseMetric, "rmse")
    value, _, _ = rmse._compute(
        {}, evaluation_payload={"a": 2.0, "b": 3.0}, task_scope=_FixedScope()
    )
    assert value == pytest.approx(0.7071067811865476, abs=1e-15)

    mae = _metric(scoring_module, scoring_module.TessRotationMaeMetric, "mae")
    value, _, _ = mae._compute(
        {}, evaluation_payload={"a": 2.0, "b": 3.0}, task_scope=_FixedScope()
    )
    assert value == 0.5


def test_constant_mean_predictor_scores_exactly_zero(scoring_module):
    """R-squared's defining property, over a population with real spread.

    This is the first thing to break if the total sum of squares is ever
    taken over the training population, a fixed constant, or the predictions
    instead of the evaluation scope's own targets.
    """
    targets = {"a": -0.5, "b": 1.0, "c": 2.25, "d": 17.0}

    class Scope:
        def truth(self):
            return targets

    mean = sum(targets.values()) / len(targets)
    r2 = _metric(scoring_module, scoring_module.TessRotationR2Metric, "r2")
    value, _, _ = r2._compute(
        {}, evaluation_payload={key: mean for key in targets}, task_scope=Scope()
    )
    assert value == pytest.approx(0.0, abs=1e-12)


def test_partial_deliverable_is_refused(scoring_module):
    """A missing prediction is an error, never an imputed value.

    Filling it with the target mean would flatter the score and filling it
    with zero would punish it; both produce a plausible number computed from
    something the model never said.
    """
    r2 = _metric(scoring_module, scoring_module.TessRotationR2Metric, "r2")
    with pytest.raises(ValueError, match="covers 1 of 2"):
        r2._compute({}, evaluation_payload={"a": 2.0}, task_scope=_FixedScope())


def test_zero_variance_scope_is_refused_not_scored(scoring_module):
    """R-squared is undefined when every scoped target is identical.

    Returning any number here — 0.0, 1.0 or a NaN — would be a scope
    construction defect reported as a model result.
    """

    class Flat:
        def truth(self):
            return {"a": 1.25, "b": 1.25}

    r2 = _metric(scoring_module, scoring_module.TessRotationR2Metric, "r2")
    with pytest.raises(ValueError, match="target variance is"):
        r2._compute({}, evaluation_payload={"a": 1.0, "b": 2.0}, task_scope=Flat())


# ------------------------------------------------------------- staging guard


def test_staging_refuses_a_data_root_holding_test_artifacts(tmp_path):
    """The operative test-split isolation, exercised rather than asserted.

    The type-level refusal proves no scope can NAME the held-out split; it
    does nothing about a file sitting in the same directory that generated
    code could simply open. This guard is what keeps it out, so a run that
    exits zero after printing the refusal would be the defect.
    """
    (tmp_path / "tess_regression_test.parquet").touch()
    completed = subprocess.run(
        [
            sys.executable,
            str(PACK / "tools" / "stage_data.py"),
            "--source",
            str(tmp_path),
            "--data_dir",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # The destination is clean here; the SOURCE holds the test artifact, so
    # staging must fail on the missing source split rather than silently
    # copying. Either way a non-zero status is required.
    assert completed.returncode != 0, completed.stdout

    dirty = tmp_path / "dirty"
    dirty.mkdir()
    (dirty / "tess_regression_test.parquet").touch()
    completed = subprocess.run(
        [
            sys.executable,
            str(PACK / "tools" / "stage_data.py"),
            "--source",
            str(tmp_path),
            "--data_dir",
            str(dirty),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert (
        "must never hold the held-out test population"
        in completed.stderr + completed.stdout
    )


# ------------------------------------------------------ staged-data integration


def test_materialized_batch_matches_the_declared_forward_contract(
    data_path, full_request
):
    """The declared contract is [B, 1, 1024] float32; nothing checks it for us.

    A mismatch here surfaces in production as an opaque shape or dtype error
    deep inside a generated model's first conv layer.
    """
    from execute_tools.task_data_path import EvalMaterializationParams

    data_dir = _staged_data_dir()
    scope = data_path.build_eval_scope(full_request)
    dataset = data_path.validation_dataset(
        scope, EvalMaterializationParams(data_dir=str(data_dir))
    )
    assert len(dataset) == len(scope.rows)

    model_input, target = dataset[0]
    assert tuple(model_input.shape) == (1, 1024)
    assert str(model_input.dtype) == "torch.float32"
    assert tuple(target.shape) == (1,)
    assert str(target.dtype) == "torch.float32"


def test_normalization_is_applied_before_padding(data_path_module):
    """A short curve's z-score must not be shifted by its own padding.

    Padding first and normalizing second is the plausible wrong order: it
    produces finite, reasonable-looking values, so only an explicit check
    over a curve whose padded tail dominates its length can see it.
    """
    import numpy as np

    observed = np.array([0.0, 2.0], dtype=np.float64)
    result = data_path_module.normalize_curve(observed, 8)

    assert result.shape == (8,)
    # The two OBSERVED samples carry the z-score of [0, 2]: mean 1, population
    # std 1, so exactly -1 and +1. Normalizing after padding would instead
    # give the mean of [0, 2, 2, 2, 2, 2, 2, 2].
    assert result[0] == pytest.approx(-1.0)
    assert result[1] == pytest.approx(1.0)
    # The tail repeats the last OBSERVED value in normalized space.
    assert result[2:].tolist() == pytest.approx([1.0] * 6)


def test_a_constant_curve_normalizes_to_zeros_rather_than_raising(data_path_module):
    """A flat light curve is a real observation, not a malformed one.

    Dividing by a zero standard deviation would produce NaN, which would
    then travel silently into the model and out into a deliverable that the
    scoreability contract has to catch much later.
    """
    import numpy as np

    result = data_path_module.normalize_curve(np.full(16, 3.5), 16)
    assert not np.isnan(result).any()
    assert (result == 0.0).all()
