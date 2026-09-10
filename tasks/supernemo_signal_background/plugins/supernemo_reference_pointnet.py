"""Small known-good pointwise-set baseline for SuperNEMO events."""

from __future__ import annotations

import torch
from pydantic import BaseModel, Field
from torch import nn

PLUGIN_MODEL_TYPE = "supernemo_reference_pointnet"
PLUGIN_OUTPUT_TYPE = "classifier"


class SuperNemoReferenceConfig(BaseModel):
    model_type: str = Field(default=PLUGIN_MODEL_TYPE)
    segmentation_size: int = Field(default=224, ge=224, le=224)
    batch_size: int = Field(default=256, ge=1, le=4096)
    hidden_dim: int = Field(default=128, ge=32, le=512)


class SuperNemoReferencePointNet(nn.Module):
    def __init__(self, config: SuperNemoReferenceConfig) -> None:
        super().__init__()
        width = config.hidden_dim
        self.encoder = nn.Sequential(
            nn.Conv1d(11, width, 1),
            nn.GELU(),
            nn.Conv1d(width, width, 1),
            nn.GELU(),
        )
        self.head = nn.Sequential(
            nn.Linear(width + 5, width), nn.GELU(), nn.Linear(width, 2)
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        mask = inputs[..., 0] > 0.5
        encoded = self.encoder(inputs.transpose(1, 2))
        pooled = encoded.masked_fill(~mask[:, None, :], -torch.inf).amax(dim=2)
        event = inputs[:, 0, 6:11]
        return self.head(torch.cat((pooled, event), dim=1))


PLUGIN_CONFIG_CLASS = SuperNemoReferenceConfig
PLUGIN_MODEL_CLASS = SuperNemoReferencePointNet
