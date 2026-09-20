"""Frozen experiment prior bindings; no task edits or agent scheduling."""

from __future__ import annotations

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
from experiments.tidmad.information_treatments.frozen_prior import (
    frozen_prior,
    full_analysis_policy,
)


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
    if enabled:
        artifact = frozen_prior(root).advice
        if treatment.advice_path != artifact.verify(root):
            raise ValueError("Full treatment must bind the shared frozen V7 advice")
    return treatment


def candidate_analysis_policy(root: Path, band: str) -> DataAnalysisWorkflowConfig:
    """Compatibility name for callers; now returns the frozen V7 policy."""
    return full_analysis_policy(root, band)


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
