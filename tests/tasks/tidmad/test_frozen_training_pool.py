"""The frozen TIDMAD parent is shared across rounds and band selections."""

from __future__ import annotations

from pathlib import Path

import pytest
from execute_tools.dataset_config import DatasetProfile, bind_dataset_profile
from execute_tools.task_data_path import ScopeBuildRequest, bind_task_data_path
from nodes.ml_hyperparameter_tune_agent.scope_acquisition import acquire_attempt_scopes
from workflows.task_composition import compose_task_data_path_from_manifest

from tasks.tidmad.runtime.tidmad_data_path import TidmadFrozenPoolDataPath, TidmadScope

ROOT = Path(__file__).resolve().parents[3]
PROFILE = DatasetProfile.model_validate_json(
    (ROOT / "tasks/tidmad/resolved/dataset_profile.json").read_text(encoding="utf-8")
)
BANDS = ("0-3", "4-9", "10-14", "15-19")


def _request(*, band: str, portion: float, seed: int, kind: str) -> ScopeBuildRequest:
    return ScopeBuildRequest(
        round_kind=kind,
        selection_strategy="snapshot",
        portion=portion,
        seed=seed,
        subset_ref=band,
        task_parameters={"seg_size": 40_000},
    )


@pytest.mark.parametrize("band", BANDS)
def test_trial_is_relative_and_formal_is_the_same_parent_for_each_band(
    band: str,
) -> None:
    impl = TidmadFrozenPoolDataPath()
    with bind_dataset_profile(PROFILE):
        formal_request = _request(band=band, portion=0.1, seed=11, kind="formal")
        parent = impl.build_frozen_training_pool(formal_request)
        formal = impl.build_frozen_training_pool(
            _request(band=band, portion=0.1, seed=999, kind="formal")
        )
        trial = impl.sample_training_pool(
            parent.scope, _request(band=band, portion=0.5, seed=12, kind="trial")
        )
    assert isinstance(parent.scope, TidmadScope)
    assert isinstance(trial, TidmadScope)
    assert parent.source_portion == 0.1
    assert formal.scope.sample_set == parent.scope.sample_set
    assert all(len(indices) == 20 for indices in parent.scope.sample_set.values())
    assert all(len(indices) == 10 for indices in trial.sample_set.values())
    assert impl.training_scope_is_contained(trial, parent.scope)
    assert set(parent.scope.sample_set) == set(range(*_band_range(band)))


def _band_range(band: str) -> tuple[int, int]:
    first, last = (int(value) for value in band.split("-"))
    return first, last + 1


def test_composed_acquisition_uses_frozen_parent_not_legacy_builder() -> None:
    impl = TidmadFrozenPoolDataPath()
    knobs = {
        "composed": True,
        "mode": "trial",
        "trial_strategy": "snapshot",
        "trial_portion": 0.5,
        "eval_strategy": "snapshot",
        "eval_portion": 1.0,
        "train_sampling_seed": 17,
        "eval_sampling_seed": 18,
        "target_files": None,
        "subset": None,
        "validation_max_samples": None,
        "task_parameters": {"seg_size": 40_000},
    }
    with bind_dataset_profile(PROFILE), bind_task_data_path(impl):
        trial = acquire_attempt_scopes(**knobs)
        formal = acquire_attempt_scopes(
            **{**knobs, "mode": "formal", "trial_portion": 0.1}
        )
    assert isinstance(trial.training, TidmadScope)
    assert isinstance(formal.training, TidmadScope)
    assert all(len(indices) == 10 for indices in trial.training.sample_set.values())
    assert all(len(indices) == 20 for indices in formal.training.sample_set.values())
    assert all(len(indices) == 200 for indices in formal.evaluation.sample_set.values())
    assert impl.training_scope_is_contained(trial.training, formal.training)


def test_tampered_manifest_refuses_before_scope_construction(tmp_path: Path) -> None:
    impl = TidmadFrozenPoolDataPath()
    tampered = tmp_path / "manifest.json"
    tampered.write_text('{"sample_set": {}}')
    impl._POOL_PATH = tampered
    with bind_dataset_profile(PROFILE), pytest.raises(ValueError, match="digest mismatch"):
        impl.build_frozen_training_pool(
            _request(band="0-3", portion=0.1, seed=11, kind="formal")
        )


def test_composition_loads_opt_in_capability_from_the_public_manifest() -> None:
    implementation = compose_task_data_path_from_manifest(
        str(ROOT / "tasks/tidmad/compositions/continuous_regression_frozen_pool.yaml")
    )
    assert implementation.task_data_path_id == "tidmad"
    assert callable(implementation.build_frozen_training_pool)
    assert callable(implementation.sample_training_pool)
