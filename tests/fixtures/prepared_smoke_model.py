"""Tiny operator-owned qualification model, never a formal proposal or prior."""

from typing import Literal

import torch
from pydantic import BaseModel, ConfigDict, Field

PLUGIN_MODEL_TYPE = "prepared_smoke_regressor"


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_type: Literal["prepared_smoke_regressor"] = "prepared_smoke_regressor"
    segmentation_size: int = Field(ge=1)
    batch_size: int = Field(default=16, ge=1)


class Model(torch.nn.Module):
    def __init__(self, config: Config):
        super().__init__()
        self.head = torch.nn.Linear(4, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(torch.cat((x.mean(dim=-1), x.square().mean(dim=-1)), dim=1))


PLUGIN_CONFIG_CLASS = Config
PLUGIN_MODEL_CLASS = Model
PLUGIN_OUTPUT_TYPE = "regressor"
