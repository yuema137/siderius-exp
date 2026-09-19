"""Candidate experiment bindings; no task edits, agent scheduling or execution."""

from __future__ import annotations

import copy
from enum import StrEnum
from pathlib import Path

import yaml
from workflows.data_analysis_composition import DataAnalysisWorkflowConfig

from experiments.shared.information_treatment import (
    AdviceMode,
    ModuleState,
    ResolvedInformationTreatment,
    resolve_information_treatment,
)
from experiments.tidmad.main_fixed_workflow.band_inputs import BANDS


class Prior(StrEnum):
    ON = "on"
    OFF = "off"


def resolve_prior(root: Path, prior: Prior) -> ResolvedInformationTreatment:
    """Reuse the matching fixed arm's exact information authority and advice bytes."""
    prior = Prior(prior)
    suffix = "full" if prior is Prior.ON else "no-prior"
    treatment = resolve_information_treatment(
        root / f"experiments/tidmad/information_treatments/main-fixed-{suffix}.yaml",
        repository_root=root,
        adapter="siderius",
        required_modules=("literature_review", "data_analysis"),
    )
    enabled = prior is Prior.ON
    if (
        (treatment.declaration.advice.mode is AdviceMode.ENABLED) != enabled
        or treatment.module_states["data_analysis"]
        is not (ModuleState.ENABLED if enabled else ModuleState.DISABLED)
        or treatment.module_states["literature_review"] is not ModuleState.ENABLED
    ):
        raise ValueError(
            "prior must switch advice and Data Analysis together; literature stays on"
        )
    if treatment.task_package_path != root / "tasks/tidmad":
        raise ValueError("treatment does not reference the common TIDMAD task")
    return treatment


def candidate_analysis_policy(root: Path, band: str) -> DataAnalysisWorkflowConfig:
    """Adapt an existing raw-only diagnostic policy, explicitly not a scientific freeze."""
    source = (
        root
        / "experiments/tidmad/data_analysis_raw_characterization/analysis_config.yaml"
    )
    raw = copy.deepcopy(yaml.safe_load(source.read_text()))
    indices = list(BANDS[band])
    raw["scientific_goal"] = (
        "Characterize authorized raw waveform inputs in the selected band."
    )
    raw["scientific_constraints"] = [
        f"Every certified selection must cover the selected files {indices} or refuse.",
        "Findings concern sampled raw validation windows, not unseen data or hidden targets.",
        "Use the declared physical cadence; distinguish measured findings from hypotheses.",
    ]
    asset = raw["available_assets"][0]
    asset["asset_id"] = "tidmad-band-validation-input"
    asset["description"] = "Raw validation input windows from the selected band."
    asset["location"]["task_data_path_id"] = "tidmad_frozen_training_pool"
    asset["authorized_scope"]["data_scope"]["file_indices"] = indices
    asset["metadata"]["band_file_indices"] = indices
    raw["declared_scope"]["raw_input_asset_ids"] = [asset["asset_id"]]
    raw["access_policy"]["policy_id"] = f"tidmad-orchestrator-candidate-{band}"
    raw["access_policy"]["purpose"] = (
        "Candidate raw-only band analysis, pending main-run freeze."
    )
    return DataAnalysisWorkflowConfig.model_validate(raw)


def composition_overlay(root: Path, analysis_path: Path | None) -> dict:
    """Relocate existing manifest references without changing any task declaration."""
    source = root / "tasks/tidmad/compositions/continuous_regression_frozen_pool.yaml"
    payload = yaml.safe_load(source.read_text())

    def relocate(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"file", "config", "declaration"} and isinstance(item, str):
                    value[key] = str((source.parent / item).resolve())
                else:
                    relocate(item)
        elif isinstance(value, list):
            for item in value:
                relocate(item)

    relocate(payload)
    payload["data_analysis"] = (
        {"enabled": True, "config": str(analysis_path)}
        if analysis_path is not None
        else {"enabled": False}
    )
    return payload
