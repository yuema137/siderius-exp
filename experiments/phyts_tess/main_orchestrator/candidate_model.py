"""What a scoreable PhyTS TESS candidate is, stated once for both sides.

The caller's exporter imports this to prove that the candidate it wrote loads
the way the scorer will load it; `tess-score` imports it to load it. One
contract and one loader, so the two processes cannot disagree about what
crosses between them.

A candidate is a directory of code-free artifacts: a TorchScript `model.pt`,
its matching `weights.pth`, a `contract.json` naming the tensor contract, and
the reconstruction metadata the framework's native export writes. Retained
source under `model/` is for diagnosis and is never imported by the scorer.

Shape follows `deployments/tidmad_coding_agent_baseline/tools/segment_inference.py`
and `archive_candidate.py`. The contract itself is this task's: one channel of
1024 float32 samples in, one scalar per curve out.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import torch
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tasks.phyts_tess.runtime.tess_data_path import SEQUENCE_LENGTH

__all__ = [
    "CONTRACT_VERSION",
    "MAX_INFERENCE_BATCH",
    "REQUIRED_CANDIDATE_FILES",
    "TessModelContract",
    "candidate_tree_digest",
    "load_candidate_model",
    "predict_rotation",
    "validate_candidate_identity",
    "validate_candidate_source",
]

CONTRACT_VERSION = "phyts-tess-rotation-model-v1"

#: The task data path's own ceiling (`max_inference_batch_size`); a candidate
#: may ask for less, never more.
MAX_INFERENCE_BATCH = 256

REQUIRED_CANDIDATE_FILES = (
    "contract.json",
    "model.pt",
    "weights.pth",
    "native_reconstruction.json",
    "train_config.json",
)

#: A candidate carries a model, not data. Any of these inside it means the
#: caller packed something that is not a model.
_DATA_SUFFIXES = frozenset({".npz", ".npy", ".csv", ".parquet", ".h5", ".hdf5"})

_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class TessModelContract(BaseModel):
    """The fixed evaluator-facing tensor contract plus a bounded batch choice."""

    model_config = ConfigDict(extra="allow", frozen=True)

    version: Literal["phyts-tess-rotation-model-v1"]
    sequence_length: int
    input_dtype: Literal["float32"]
    output_kind: Literal["continuous_scalar"]
    inference_batch_size: int = Field(default=64, ge=1, le=MAX_INFERENCE_BATCH)

    @field_validator("sequence_length")
    @classmethod
    def _frozen_window(cls, value: int) -> int:
        # The window is the task's, declared once in the data path. A contract
        # naming another length describes a model the task cannot feed.
        if value != SEQUENCE_LENGTH:
            raise ValueError(
                f"contract sequence_length {value} differs from the task's "
                f"{SEQUENCE_LENGTH}"
            )
        return value


def validate_candidate_identity(candidate_id: str) -> None:
    """Refuse identities that cannot safely become evaluator-owned paths."""
    if not _IDENTITY.fullmatch(candidate_id):
        raise ValueError(f"invalid candidate identity: {candidate_id!r}")


def validate_candidate_source(source: Path) -> None:
    """Refuse incomplete, transient, data-bearing, or linked candidate trees."""
    if not source.is_dir():
        raise ValueError(f"candidate source is not a directory: {source}")
    for name in REQUIRED_CANDIDATE_FILES:
        if not (source / name).is_file():
            raise ValueError(f"candidate source is missing {name}: {source}")
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"candidate source contains a symlink: {path}")
        if path.is_file() and (
            path.name.endswith(".tmp") or path.suffix in _DATA_SUFFIXES
        ):
            raise ValueError(
                f"candidate source contains a temporary/data artifact: {path}"
            )


def _manifest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def candidate_tree_digest(root: Path) -> str:
    """Hash the exact candidate-file manifest using a stable encoding."""
    payload = json.dumps(
        _manifest(root), sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _load_contract(candidate: Path) -> TessModelContract:
    payload = json.loads((candidate / "contract.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("contract.json must contain a JSON object")
    return TessModelContract.model_validate(payload)


def _load_state_dict(path: Path) -> dict[str, torch.Tensor]:
    payload: Any = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict) or not payload:
        raise ValueError("weights.pth must contain a non-empty model state_dict")
    if not all(
        isinstance(key, str) and isinstance(value, torch.Tensor)
        for key, value in payload.items()
    ):
        raise ValueError("weights.pth must map parameter names directly to tensors")
    return payload


def load_candidate_model(
    candidate: Path, device: torch.device
) -> tuple[torch.jit.ScriptModule, TessModelContract]:
    """Load a code-free serialized model and prove its companion weights match.

    `torch.jit.load` executes no Python from the candidate; the retained
    `model/` source is never imported here.
    """
    contract = _load_contract(candidate)
    model = torch.jit.load(str(candidate / "model.pt"), map_location="cpu")
    submitted = _load_state_dict(candidate / "weights.pth")
    embedded = model.state_dict()
    if set(submitted) != set(embedded):
        raise ValueError("weights.pth keys do not match model.pt")
    if sum(value.numel() for value in model.parameters()) <= 0:
        raise ValueError("candidate must contain learned model parameters")
    for name, expected in embedded.items():
        actual = submitted[name]
        if actual.shape != expected.shape or actual.dtype != expected.dtype:
            raise ValueError(f"weights.pth tensor contract differs for {name}")
        if not _same_values(actual.cpu(), expected.cpu()):
            raise ValueError(
                f"weights.pth tensor bytes differ from model.pt for {name}"
            )
    model.eval().to(device)
    return model, contract


def _same_values(actual: torch.Tensor, expected: torch.Tensor) -> bool:
    """Element-wise identity that treats NaN as equal to NaN.

    `torch.equal` follows IEEE (`NaN != NaN`), which would make a diverged
    model — NaN weights faithfully present in BOTH files — refused here as
    "bytes differ". Its refusal belongs to the scoreability contract, which
    names the reason (`numerical`); the loader only asks whether the two
    files carry the same parameters.
    """
    if not actual.is_floating_point():
        return torch.equal(actual, expected)
    same = torch.eq(actual, expected) | (torch.isnan(actual) & torch.isnan(expected))
    return bool(same.all())


def predict_rotation(
    model: torch.jit.ScriptModule,
    inputs: Sequence[torch.Tensor],
    *,
    batch_size: int,
    device: torch.device,
) -> list[float]:
    """One predicted rotation frequency per `[1, 1024]` float32 curve, in order.

    Shape and dtype are enforced on both sides of the model. Values are not:
    a non-finite prediction is the scoreability contract's to refuse by name,
    which is more useful than an exception here.
    """
    if not 1 <= batch_size <= MAX_INFERENCE_BATCH:
        raise ValueError(f"batch_size must be within 1..{MAX_INFERENCE_BATCH}")
    predictions: list[float] = []
    with torch.inference_mode():
        for start in range(0, len(inputs), batch_size):
            chunk = list(inputs[start : start + batch_size])
            for curve in chunk:
                if (
                    tuple(curve.shape) != (1, SEQUENCE_LENGTH)
                    or curve.dtype != torch.float32
                ):
                    raise ValueError(
                        f"candidate input must be a [1, {SEQUENCE_LENGTH}] float32 "
                        f"curve; got {tuple(curve.shape)} {curve.dtype}"
                    )
            batch = torch.stack(chunk).to(device)
            output = model(batch)
            if not isinstance(output, torch.Tensor):
                raise TypeError("candidate must return one tensor")
            if output.shape[0] != batch.shape[0] or output.numel() != batch.shape[0]:
                raise ValueError(
                    f"candidate produced output shape {tuple(output.shape)} for a "
                    f"batch of {batch.shape[0]} curves; one scalar per curve is required"
                )
            if not output.is_floating_point():
                raise ValueError(
                    f"candidate output must be floating point; got {output.dtype}"
                )
            predictions.extend(
                float(value) for value in output.reshape(-1).cpu().tolist()
            )
    return predictions
