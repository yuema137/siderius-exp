"""TIDMAD ownership of the historical Trial/Formal SampleSet policy."""

from __future__ import annotations

import json
from pathlib import Path

from agent.schemas.hyperparam_tuning import ExperimentPlan, HyperparamTuningInput
from execute_tools.dataset_config import DatasetProfile, bind_dataset_profile
from execute_tools.sample_set_builder import build_sample_set
from nodes.ml_hyperparameter_tune_agent import _resolve_sample_set_cfg
from tasks.tidmad.runtime.profile import tidmad_topology

TASK_ROOT = Path(__file__).resolve().parents[3] / "tasks" / "tidmad"


def _profile() -> DatasetProfile:
    payload = json.loads((TASK_ROOT / "resolved" / "dataset_profile.json").read_text())
    return DatasetProfile.model_validate(payload)


def _input(tmp_path: Path, **overrides) -> HyperparamTuningInput:
    payload = {
        "model_type": "punet",
        "file_index": 6,
        "max_rounds": 1,
        "storage": {
            "backend": "local",
            "local": {"workspace": str(tmp_path), "run_name": "formal-scope"},
        },
    }
    payload.update(overrides)
    return HyperparamTuningInput(**payload)


def _plan(**overrides) -> ExperimentPlan:
    payload = {
        "model_cfg": {"segmentation_size": 10_000},
        "train_cfg": {"epochs": 1},
        "loss_cfg": {"loss_type": "ce"},
        "is_trial": True,
        "trial_strategy": "anchors",
        "trial_portion": 0.02,
        "train_portion": 0.3,
        "eval_strategy": "anchors",
        "eval_portion": 0.02,
        "hypothesis": "scope policy witness",
        "expected_score": 1.0,
        "memory_update": "none",
    }
    payload.update(overrides)
    return ExperimentPlan(**payload)


def _build_snapshot(profile: DatasetProfile, portion: float) -> dict[int, list[int]]:
    with bind_dataset_profile(profile):
        return build_sample_set(
            is_trial=True,
            trial_strategy="snapshot",
            trial_portion=portion,
            seed=0,
        )


def test_formal_defaults_resolve_the_historical_tidmad_training_scope(
    tmp_path: Path,
) -> None:
    profile = _profile()
    topology = tidmad_topology(profile)
    config = _resolve_sample_set_cfg("formal", _input(tmp_path), _plan())

    assert config["trial_strategy"] == "snapshot"
    assert config["trial_portion"] == 0.1
    assert config["train_portion"] == 1.0

    sample_set = _build_snapshot(profile, config["trial_portion"])
    assert len(sample_set) == topology.dataset.num_files == 20
    assert {len(segments) for segments in sample_set.values()} == {20}


def test_formal_eval_ignores_the_planner_and_resolves_full_snapshot(
    tmp_path: Path,
) -> None:
    profile = _profile()
    topology = tidmad_topology(profile)
    config = _resolve_sample_set_cfg(
        "formal",
        _input(tmp_path),
        _plan(eval_strategy="anchors", eval_portion=0.01),
    )

    assert config["eval_strategy"] == "snapshot"
    assert config["eval_portion"] == 1.0
    sample_set = _build_snapshot(profile, config["eval_portion"])
    assert len(sample_set) == topology.dataset.num_files
    assert {len(segments) for segments in sample_set.values()} == {
        topology.dataset.segments_per_file
    }


def test_formal_training_override_remains_operator_owned(tmp_path: Path) -> None:
    profile = _profile()
    config = _resolve_sample_set_cfg(
        "formal", _input(tmp_path, formal_portion=0.5), _plan()
    )

    assert config["trial_portion"] == 0.5
    assert {len(segments) for segments in _build_snapshot(profile, 0.5).values()} == {
        100
    }


def test_trial_anchor_selection_comes_from_the_task_declaration(tmp_path: Path) -> None:
    profile = _profile()
    config = _resolve_sample_set_cfg(
        "trial",
        _input(tmp_path),
        _plan(trial_strategy="anchors", trial_portion=0.05, train_portion=0.25),
    )

    assert config["trial_strategy"] == "anchors"
    assert config["train_portion"] == 0.25
    with bind_dataset_profile(profile):
        sample_set = build_sample_set(
            is_trial=True,
            trial_strategy=config["trial_strategy"],
            trial_portion=config["trial_portion"],
            seed=0,
        )
    assert set(sample_set) == set(profile.anchor_selection_files)
