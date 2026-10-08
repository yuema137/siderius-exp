"""Experiment choices for the unchanged Cancer gene-classification task."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tutorials.shared.gpu_check import ExpectedGpu, VramBudget


class CancerExperiment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["cancer-tutorial-v1"] = "cancer-tutorial-v1"
    infra_checkout: Path
    data_dir: Path
    workspace: Path
    composition: Path
    llm_config: Path
    workflow: Path
    run_name: str = Field(
        default="cancer_demo_001", pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$"
    )
    gpu: ExpectedGpu | None = None
    iterations: int = Field(default=3, ge=1, le=100)
    rounds: int = Field(default=2, ge=2, le=20)
    epochs: int = Field(default=1, ge=1, le=1000)
    trial_train_label_fraction: float = Field(default=1.0, ge=0.01, le=1)
    trial_eval_label_fraction: float = Field(default=1.0, ge=0.01, le=1)
    formal_train_label_fraction: float = Field(default=1.0, ge=0.01, le=1)
    formal_eval_label_fraction: float = Field(default=1.0, ge=0.01, le=1)
    trial_minutes: float = Field(default=2, gt=0, le=120)
    formal_minutes: float = Field(default=5, gt=0, le=120)
    vram_gib: VramBudget = 10.0
    trial_vram_gib: VramBudget | None = None
    formal_vram_gib: VramBudget | None = None
    advice_file: None = None

    @field_validator(
        "infra_checkout",
        "data_dir",
        "workspace",
        "composition",
        "llm_config",
        "workflow",
    )
    @classmethod
    def absolute_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError(
                "use absolute paths, independent of the notebook directory"
            )
        return value.resolve()
