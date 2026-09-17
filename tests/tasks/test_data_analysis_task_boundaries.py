"""Task packages may enable analysis only when their data path owns the view.

The four shapes in this matrix are waveform regression, image classification,
video prediction, and graph classification. Only TIDMAD currently declares an
executable analysis materializer. The other tasks must fail at composition,
not later when an agent tries to read a nonexistent generic view.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from execute_tools.analysis_materialization import (
    TaskAnalysisCapability,
    TaskHistoricalInferenceInputCapability,
)
from workflows.data_analysis_composition import compose_workflow_data_analysis

from agent.schemas.task_config import ForwardContract
from execute_tools.task_registration_scope import run_registration_scope
from workflows.task_composition import compose_run_task_bindings

ROOT = Path(__file__).resolve().parents[2]


def _analysis_config(tmp_path: Path, *, task_id: str) -> tuple[Path, Path]:
    """A valid caller policy, so refusal isolates the task capability gate."""

    profile = tmp_path / "profile.json"
    profile.write_text('{"synthetic":true}', encoding="utf-8")
    payload = {
        "scientific_goal": "Characterize validation inputs.",
        "input_description": "Task-owned validation observations.",
        "available_assets": [
            {
                "asset_id": "validation-input",
                "asset_type": "dataset",
                "description": "Synthetic task-owned validation input.",
                "location": {
                    "kind": "task_data",
                    "task_data_path_id": task_id,
                    "dataset_profile_sha256": hashlib.sha256(profile.read_bytes()).hexdigest(),
                    "logical_role": "validation_features",
                },
                "provenance": {"producer": "task-boundary-test"},
                "authorized_scope": {
                    "kind": "artifact_intrinsic",
                    "split_id": "validation",
                    "description": "Validation observations.",
                },
                "split_id": "validation",
            }
        ],
        "declared_scope": {"raw_input_asset_ids": ["validation-input"]},
        "access_policy": {
            "policy_id": "task-boundary-test",
            "policy_version": 1,
            "purpose": "Scientific characterization.",
            "split_rules": [{"split_id": "validation", "data_visible": True}],
        },
        "resource_envelope": {
            "wall_time_budget_s": 30,
            "per_skill_timeout_s": 10,
            "preferred_device": "cpu",
        },
        "builtin_skill_packs": ["core-analysis"],
    }
    path = tmp_path / "analysis.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, profile


def test_tidmad_enabled_edge_resolves_only_raw_input_and_model_inference() -> None:
    """The real task composition must reach its own certified materializer."""

    with run_registration_scope():
        composition = compose_run_task_bindings(
            str(ROOT / "experiments/tidmad/data_analysis_pair/task_composition_on.yaml")
        )
        task = composition.task_data_path
        analysis = composition.data_analysis
        assert isinstance(task, TaskAnalysisCapability)
        assert isinstance(task, TaskHistoricalInferenceInputCapability)
        assert analysis is not None
        assert analysis.declared_scope.raw_input_asset_ids == ("tidmad-high-band-validation-input",)
        assert analysis.historical_inference_base_asset_id == ("tidmad-high-band-validation-input")
        assert not analysis.access_policy.permits(split_id="validation", information_class="target")


@pytest.mark.parametrize(
    ("module_name", "class_name"),
    [
        ("tasks.oxford_iiit_pet.runtime.pets_data_path", "PetsTaskDataPath"),
        ("tasks.davis_future_prediction.runtime.davis_data_path", "DavisTaskDataPath"),
        ("tasks.cancer_gene_identification.plugins._cancer_gene_task", "CancerGeneTaskDataPath"),
    ],
)
def test_task_without_analysis_materializer_refuses_enabled_edge(
    tmp_path: Path, module_name: str, class_name: str
) -> None:
    """An experiment policy cannot invent a task-owned analysis view."""

    with run_registration_scope():
        task = getattr(importlib.import_module(module_name), class_name)()
        config, profile = _analysis_config(tmp_path, task_id=task.task_data_path_id)
        with pytest.raises(ValueError, match="does not implement TaskAnalysisCapability"):
            compose_workflow_data_analysis(
                {"enabled": True, "config": config.name},
                manifest_path=str(tmp_path / "task.yaml"),
                task_data_path=task,
                task_data_path_id=task.task_data_path_id,
                task_description="A scientific task with no analysis materializer.",
                forward_contract=ForwardContract(),
                metric=SimpleNamespace(spec=SimpleNamespace(id="error", direction="lower")),
                dataset_profile_ref="profile.json",
                dataset_profile_path=str(profile),
            )
