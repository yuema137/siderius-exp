"""PhyTS TESS reference 1-D CNN — the pack's known-good executable baseline.

A baseline, NOT a candidate: a small deterministic convolutional stack with
no pretrained weights, no augmentation and no hyperparameter search. Its job
is to prove the forward contract executes end to end and to give a real run
something to beat, not to be competitive with the PhyTS state of the art
(S4D reaches R-squared 0.665 on this task; a stack this size will not).

Loaded DYNAMICALLY through the plugin mechanism; nothing in the framework
imports this module.

Forward boundary (the pack's declared contract):
``[B, 1, 1024] float32 -> [B, 1] float32``.

**No output activation, deliberately.** The target is an unbounded real
quantity that includes a small number of negative values, so a ReLU or
sigmoid head would make part of the target range unreachable and cap the
achievable R-squared for reasons that have nothing to do with the science.
"""

import torch
from pydantic import BaseModel, Field
from torch import nn

PLUGIN_MODEL_TYPE = "tess_reference_cnn"


class TessReferenceCnnConfig(BaseModel):
    model_type: str = Field(
        default="tess_reference_cnn", description="Plugin model type key."
    )
    #: Engine-residue compatibility field: the streaming engine reads
    #: `model_cfg.segmentation_size` at run start. Nothing on the TESS path
    #: consumes it; it mirrors the frozen input length so a reader who does
    #: look at it is not misled.
    segmentation_size: int = Field(default=1024, ge=1)
    batch_size: int = Field(default=64, ge=1)
    hidden_channels: int = Field(default=16, ge=4, le=128)


PLUGIN_CONFIG_CLASS = TessReferenceCnnConfig


class TessReferenceCnn(nn.Module):
    """Three strided conv blocks, global average pool, linear head.

    Kernel width 7 rather than 3: the signal is periodic variability spread
    over the whole window, so the first layer is given a receptive field
    wide enough to see a local oscillation rather than a three-sample edge.
    Global average pooling over time follows from the same fact — the answer
    does not depend on WHERE in the window a feature appears.

    At the default h=16: roughly 30 k parameters, comfortably inside an
    8 GiB budget.
    """

    def __init__(self, config: "TessReferenceCnnConfig"):
        super().__init__()
        h = config.hidden_channels
        self.features = nn.Sequential(
            nn.Conv1d(1, h, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(h),
            nn.ReLU(inplace=True),
            nn.Conv1d(h, 2 * h, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(2 * h),
            nn.ReLU(inplace=True),
            nn.Conv1d(2 * h, 4 * h, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(4 * h),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Linear(4 * h, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # [B, 1, 1024] float32 -> [B, 1] float32, no output activation.
        feats = self.features(x)
        return self.head(torch.flatten(feats, 1))


PLUGIN_MODEL_CLASS = TessReferenceCnn
PLUGIN_OUTPUT_TYPE = "regressor"  # [B, 1] -> one continuous rotation frequency
