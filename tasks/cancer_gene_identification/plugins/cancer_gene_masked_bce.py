"""Masked binary cross-entropy for packed transductive graph records."""

from __future__ import annotations

import torch
from pydantic import BaseModel, ConfigDict
from torch import nn

PLUGIN_LOSS_TYPE = "cancer_gene_masked_bce"
PLUGIN_LOSS_TARGET_DTYPE = "float"
PLUGIN_LOSS_REDUCTION = "mean"
PLUGIN_CAPABILITY_CONTRACT = {
    "contract_kind": "custom_loss_applicability",
    "contract_version": 1,
    "canonical_payload": '{"applicability":{"dtype":{"admissible":["float32"]},"mode":"equal_shape","rank":3},"prediction":{"axes":[{"dimension":{"dynamic":false,"fixed":null,"symbolic":"B"},"role":"batch"},{"dimension":{"dynamic":false,"fixed":null,"symbolic":"R"},"role":null},{"dimension":{"dynamic":false,"fixed":3,"symbolic":null},"role":null}],"dtype":{"admissible":["float32"]}},"supervision_target":{"axes":[{"dimension":{"dynamic":false,"fixed":null,"symbolic":"B"},"role":"batch"},{"dimension":{"dynamic":false,"fixed":null,"symbolic":"R"},"role":null},{"dimension":{"dynamic":false,"fixed":3,"symbolic":null},"role":null}],"dtype":{"admissible":["float32"]}}}',
    "sha256": "444ba6c455b1a11902552bedb44c136d73227c47477bb22bd9161be542e7862b",
}


class CancerGeneMaskedBceConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CancerGeneMaskedBce(nn.Module):
    """BCE over labeled node rows; edge and unlabeled rows never contribute."""

    def __init__(self, config: CancerGeneMaskedBceConfig) -> None:
        super().__init__()

    def forward(self, output: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if output.shape != target.shape or output.shape[-1] != 3:
            raise ValueError(
                "cancer_gene_masked_bce requires matching [B, records, 3] output and target"
            )
        selected = (target[..., 0] > 0.5) & (target[..., 1] > 0.5) & (target[..., 2] >= 0)
        if not torch.any(selected):
            raise ValueError("cancer_gene_masked_bce received no labeled node rows")
        return nn.functional.binary_cross_entropy_with_logits(
            output[..., 2][selected], target[..., 2][selected].to(output.dtype)
        )


PLUGIN_LOSS_CONFIG_CLASS = CancerGeneMaskedBceConfig
PLUGIN_LOSS_CLASS = CancerGeneMaskedBce
