"""Historical profiles preserve small-value diagnosis text at shared callers."""

import pytest
from agent.prompt_rendering import bind_prompt_profile, resolve_prompt_profile
from agent.prompt_templates.tuner.rendering import (
    render_planner_dynamics_block,
    render_reflector_dynamics_block,
    render_training_dynamics_line,
)
from agent.schemas.training_diagnosis import TrainingDiagnosis
from siderius_prompt_compat.dynamics_00dd22d0 import (
    render_training_dynamics_line as historical_line,
)
from siderius_prompt_compat.interpretation_345c802d import (
    render_interpretation_diagnosis_lines,
)


def _diagnosis():
    return TrainingDiagnosis(
        state="ok",
        validation_state="present",
        comparability="established",
        epochs_completed=3,
        train_first=0.0162345,
        train_last=0.0134567,
        train_trend="decreasing",
        validation_first=0.0187654,
        validation_last=0.0146789,
        validation_trend="decreasing",
        best_validation_epoch=1,
        final_vs_best_validation_degradation=0.00012,
        train_validation_gap_final=0.0012222,
    )


_OLD = (
    "train 0.02->0.01 (decreasing, 3 ep) · "
    "val 0.02->0.01 (decreasing; best ep 1, +0.00 after best) · "
    "gap +0.00 (comparable)"
)


@pytest.mark.parametrize(
    "profile_name",
    [
        "paper-early-v2",
        "paper-late-v2",
        "paper-tidmad-noprior-v2",
        "paper-analysis-c0467447-v2",
    ],
)
def test_historical_profile_restores_line_at_all_shared_callers(profile_name):
    diagnosis = _diagnosis()
    original = diagnosis.model_dump()
    assert "0.0162345->0.0134567" in render_training_dynamics_line(diagnosis)
    with bind_prompt_profile(resolve_prompt_profile(profile_name)):
        assert render_training_dynamics_line(diagnosis) == _OLD
        assert render_planner_dynamics_block(
            [
                {
                    "exp_id": "trial",
                    "training_diagnosis": original,
                    "training_history": {"objective_kind": "mse"},
                }
            ]
        ).endswith("- trial: [mse] " + _OLD)
        assert render_reflector_dynamics_block(diagnosis).endswith(_OLD)
        assert render_interpretation_diagnosis_lines(diagnosis, None) == [
            "  best: " + _OLD
        ]
    assert diagnosis.model_dump() == original
    assert "gap +0.0012222" in render_training_dynamics_line(diagnosis)


@pytest.mark.parametrize(
    "state, expected",
    [
        ("absent", "training dynamics: none recorded"),
        ("invalid", "training dynamics: invalid (non-finite)"),
    ],
)
def test_frozen_degenerate_diagnosis_remains_explicit(state, expected):
    assert (
        historical_line(TrainingDiagnosis(state=state, validation_state="absent"))
        == expected
    )


def test_frozen_missing_validation_and_unavailable_gap():
    diagnosis = TrainingDiagnosis(state="ok", validation_state="absent")
    assert (
        historical_line(diagnosis)
        == "train n/a->n/a (n/a) · val not recorded · gap n/a (not comparable)"
    )
    assert historical_line(None) == "training dynamics: none recorded"


def test_frozen_negative_small_gap_keeps_old_signed_rounding():
    diagnosis = _diagnosis().model_copy(
        update={"train_validation_gap_final": -0.0012222}
    )
    assert historical_line(diagnosis).endswith("gap -0.00 (comparable)")
