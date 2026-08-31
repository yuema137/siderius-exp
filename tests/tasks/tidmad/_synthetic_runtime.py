"""Self-contained synthetic runtime fixture for external TIDMAD parity tests."""


import json
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import Dataset

from agent.schemas.model_io_contract import (
    AxisRole,
    Dimension,
    DtypeAdmissibility,
    ModelIOContract,
    TensorAxis,
    TensorContract,
)
from execute_tools.task_data_path import (
    DeliverableWriteRequest,
    EpochSamplingParams,
    EvalMaterializationParams,
    EvaluationReadRequest,
)

# ---------------------------------------------------------------------------
# The synthetic task: three independent axes away from TIDMAD (child §3)
# ---------------------------------------------------------------------------


class _SyntheticPairs(Dataset):
    """float32 [4] model input; scalar int class target (Amendment 1: the
    target shares neither shape, rank nor dtype with the [2]-logit output)."""

    def __init__(self, ids: list[str], seed: int):
        gen = torch.Generator().manual_seed(seed)
        self._inputs = torch.rand((len(ids), 4), generator=gen, dtype=torch.float32)
        self._targets = torch.arange(len(ids)) % 2
        self.ids = list(ids)

    def __len__(self) -> int:
        return len(self.ids)

    def __getitem__(self, idx: int):
        return self._inputs[idx], int(self._targets[idx])


class SyntheticE2ETaskDataPath:
    task_data_path_id = "synthetic_e2e_pairs"

    def training_dataset(self, scope: object, params: EpochSamplingParams) -> Dataset:
        assert isinstance(scope, list), "synthetic scope is a plain list of string ids"
        return _SyntheticPairs(scope, seed=params.epoch_seed or 0)

    def validation_dataset(self, scope: object, params: EvalMaterializationParams) -> Dataset:
        assert isinstance(scope, list)
        return _SyntheticPairs(scope, seed=0)

    def write_deliverable(self, outputs, request: DeliverableWriteRequest) -> None:
        path = Path(request.output_dir) / f"synthetic_{request.run_name}_{request.exp_id}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for sample_id, vector in outputs:
                fh.write(json.dumps({"id": sample_id, "output": [float(v) for v in vector]}) + "\n")

    def read_evaluation_payload(self, request: EvaluationReadRequest) -> object:
        path = (
            Path(request.deliverable_dir) / f"synthetic_{request.run_name}_{request.exp_id}.jsonl"
        )
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class _TinyClassifier(nn.Module):
    """[B, 4] float -> [B, 2] logits. Registered under the synthetic type."""

    def __init__(self, cfg):
        super().__init__()
        self.net = nn.Linear(4, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


_MODEL_TYPE = "synthetic_tiny_classifier"


def _synthetic_contract() -> ModelIOContract:
    """The task's declared boundary: float32 [B, 4] in, float32 [B, 2] out.

    The contract — not any TIDMAD default — is the engine's dtype authority
    (Step 03); without it, regime-A resolution would cast the float inputs to
    TIDMAD's int site preference.
    """

    def axis(role, **dim) -> TensorAxis:
        return TensorAxis(dimension=Dimension(**dim), role=role)

    return ModelIOContract(
        input=TensorContract(
            axes=(axis(AxisRole.BATCH, symbolic="B"), axis(None, fixed=4)),
            dtype=DtypeAdmissibility(admissible=("float32",)),
        ),
        output=TensorContract(
            axes=(axis(AxisRole.BATCH, symbolic="B"), axis(AxisRole.CLASS, fixed=2)),
            dtype=DtypeAdmissibility(admissible=("float32",)),
        ),
    )
