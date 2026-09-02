"""Small known-good 1D CNN for Majorana waveforms."""

from __future__ import annotations

import torch
from pydantic import BaseModel, Field
from torch import nn

PLUGIN_MODEL_TYPE = "majorana_reference_cnn"
PLUGIN_OUTPUT_TYPE = "classifier"


class MajoranaReferenceConfig(BaseModel):
    model_type: str = Field(default=PLUGIN_MODEL_TYPE)
    segmentation_size: int = Field(default=3800, ge=3800, le=3800)
    batch_size: int = Field(default=128, ge=1, le=2048)
    width: int = Field(default=64, ge=16, le=256)


class MajoranaReferenceCnn(nn.Module):
    def __init__(self, config: MajoranaReferenceConfig) -> None:
        super().__init__()
        width = config.width
        self.features = nn.Sequential(
            nn.Conv1d(1, width, 15, stride=4, padding=7),
            nn.GELU(),
            nn.Conv1d(width, 2 * width, 9, stride=4, padding=4),
            nn.GELU(),
            nn.Conv1d(2 * width, 4 * width, 7, stride=4, padding=3),
            nn.GELU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Linear(4 * width, 2)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(inputs).squeeze(-1))


PLUGIN_CONFIG_CLASS = MajoranaReferenceConfig
PLUGIN_MODEL_CLASS = MajoranaReferenceCnn
