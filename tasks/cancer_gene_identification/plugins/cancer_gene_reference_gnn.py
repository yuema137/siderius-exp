"""Small graph-message-passing reference model for the cancer-gene pack."""

from __future__ import annotations

import torch
from pydantic import BaseModel, Field
from torch import nn

PLUGIN_MODEL_TYPE = "cancer_gene_reference_gnn"
PLUGIN_OUTPUT_TYPE = "regressor"


class CancerGeneReferenceGnnConfig(BaseModel):
    model_type: str = Field(default="cancer_gene_reference_gnn")
    segmentation_size: int = Field(default=64, ge=1)
    batch_size: int = Field(default=1, ge=1, le=1)
    hidden_dim: int = Field(default=64, ge=8, le=512)
    message_steps: int = Field(default=2, ge=1, le=4)


class CancerGeneReferenceGnn(nn.Module):
    """Sparse mean aggregation over task-packed node and edge records."""

    def __init__(self, config: CancerGeneReferenceGnnConfig) -> None:
        super().__init__()
        self.message_steps = config.message_steps
        self.encoder = nn.Linear(64, config.hidden_dim)
        self.update = nn.Linear(config.hidden_dim * 2, config.hidden_dim)
        self.head = nn.Linear(config.hidden_dim, 1)

    def forward(self, packed: torch.Tensor) -> torch.Tensor:
        outputs: list[torch.Tensor] = []
        for records in packed:
            node_mask = records[:, 0] > 0.5
            node_count = int(node_mask.sum().item())
            if node_count == 0:
                node_count = records.shape[0]
                node_mask = torch.ones(records.shape[0], dtype=torch.bool, device=records.device)
            hidden = torch.relu(self.encoder(records[:node_count, 4:68]))
            edges = records[node_count:]
            if len(edges):
                src = edges[:, 1].long().clamp(0, node_count - 1)
                dst = edges[:, 2].long().clamp(0, node_count - 1)
                for _ in range(self.message_steps):
                    aggregate = torch.zeros_like(hidden)
                    degree = torch.zeros(node_count, 1, device=hidden.device, dtype=hidden.dtype)
                    aggregate.index_add_(0, dst, hidden[src])
                    degree.index_add_(0, dst, torch.ones(len(dst), 1, device=hidden.device))
                    aggregate = aggregate / degree.clamp_min(1.0)
                    hidden = torch.relu(self.update(torch.cat([hidden, aggregate], dim=-1)))
            logits = torch.zeros(records.shape[0], device=records.device, dtype=records.dtype)
            logits[:node_count] = self.head(hidden).squeeze(-1)
            outputs.append(torch.stack([records[:, 0], records[:, 3], logits], dim=-1))
        return torch.stack(outputs)


PLUGIN_CONFIG_CLASS = CancerGeneReferenceGnnConfig
PLUGIN_MODEL_CLASS = CancerGeneReferenceGnn
