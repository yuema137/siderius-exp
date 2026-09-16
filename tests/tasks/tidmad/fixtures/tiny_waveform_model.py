"""Deterministic TIDMAD-shaped model fixture for inference equivalence only."""

import torch
from pydantic import BaseModel, Field
from torch import nn

PLUGIN_MODEL_TYPE = "tidmad_tiny_waveform"
PLUGIN_OUTPUT_TYPE = "regressor"


class TinyWaveformConfig(BaseModel):
    model_type: str = Field(default=PLUGIN_MODEL_TYPE)
    segmentation_size: int = Field(ge=1)


class TinyWaveformModel(nn.Module):
    def __init__(self, config: TinyWaveformConfig) -> None:
        super().__init__()
        self.bias = nn.Parameter(torch.tensor(0.25, dtype=torch.float32))

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return values.to(torch.float32) + self.bias


PLUGIN_CONFIG_CLASS = TinyWaveformConfig
PLUGIN_MODEL_CLASS = TinyWaveformModel
