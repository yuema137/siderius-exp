"""Evaluator-owned inference for trained models over fixed raw TIDMAD segments."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import h5py
import numpy as np
import torch
from pydantic import BaseModel, ConfigDict, Field, model_validator

SEGMENT_SIZE = 40_000
NUM_CLASSES = 256


class SegmentModelContract(BaseModel):
    """Fixed evaluator-facing tensor contract plus a bounded batch choice."""

    model_config = ConfigDict(extra="allow")

    version: Literal["tidmad-segment-model-v1", "tidmad-segment-model-v2"]
    segment_size: Literal[SEGMENT_SIZE]
    input_dtype: Literal["int64"]
    output_kind: Literal["categorical_logits", "continuous_regression"]
    num_classes: int | None = None
    inference_batch_size: int = Field(default=1, ge=1, le=32)

    @model_validator(mode="after")
    def require_matching_output_contract(self) -> SegmentModelContract:
        if self.version == "tidmad-segment-model-v1":
            if self.output_kind != "categorical_logits" or self.num_classes != NUM_CLASSES:
                raise ValueError("v1 requires 256-class categorical logits")
        elif self.output_kind != "continuous_regression" or self.num_classes is not None:
            raise ValueError("v2 requires continuous regression without num_classes")
        return self


def _load_contract(candidate: Path) -> SegmentModelContract:
    payload = json.loads((candidate / "architecture.json").read_text())
    if not isinstance(payload, dict):
        raise TypeError("architecture.json must contain a JSON object")
    return SegmentModelContract.model_validate(payload)


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
) -> tuple[torch.jit.ScriptModule, SegmentModelContract]:
    """Load a code-free serialized model and prove its companion weights match."""

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
        if not torch.equal(actual.cpu(), expected.cpu()):
            raise ValueError(f"weights.pth tensor bytes differ from model.pt for {name}")
    model.eval().to(device)
    return model, contract


def _load_regression_conversion(
    task_root: Path | None,
) -> Callable[..., np.ndarray]:
    """Load the task codec copied beside this module into the frozen harness."""

    path = (
        task_root / "tasks/tidmad/runtime/output_conversion.py"
        if task_root is not None
        else Path(__file__).with_name("frozen_output_conversion.py")
    )
    spec = importlib.util.spec_from_file_location("tidmad_frozen_output_conversion", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"frozen TIDMAD output conversion is missing: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.regression_to_storage


def _decode(
    model: torch.jit.ScriptModule,
    values: np.ndarray,
    device: torch.device,
    contract: SegmentModelContract,
    regression_conversion: Callable[..., np.ndarray] | None,
) -> np.ndarray:
    inputs = torch.from_numpy(values.astype(np.int16, copy=False) + 128).to(
        device=device,
        dtype=torch.int64,
    )
    with torch.inference_mode():
        output = model(inputs)
    required = (
        (inputs.shape[0], NUM_CLASSES, SEGMENT_SIZE)
        if contract.output_kind == "categorical_logits"
        else (inputs.shape[0], SEGMENT_SIZE)
    )
    if not isinstance(output, torch.Tensor) or tuple(output.shape) != required:
        observed = None if not isinstance(output, torch.Tensor) else tuple(output.shape)
        raise ValueError(f"model output shape {observed} does not match {required}")
    if not output.dtype.is_floating_point or not torch.isfinite(output).all():
        raise ValueError("model output must contain finite floating-point predictions")
    if contract.output_kind == "categorical_logits":
        return (output.argmax(dim=1).to(torch.int16) - 128).to(torch.int8).cpu().numpy()
    if regression_conversion is None:
        raise ValueError("continuous regression requires the frozen task-owned conversion")
    return regression_conversion(
        output.cpu().numpy(), value_offset=128, storage_dtype=np.dtype("int8")
    )


def run_segment_model(
    *,
    candidate: Path,
    input_file: Path,
    output_file: Path,
    device: torch.device | None = None,
    task_root: Path | None = None,
    required_output_kind: str | None = None,
) -> None:
    """Apply a trained model only to evaluator-created raw 40k-sample tensors."""

    device = device or torch.device("cuda")
    model, contract = load_candidate_model(candidate, device)
    if required_output_kind is not None and contract.output_kind != required_output_kind:
        raise ValueError(
            f"frozen unit requires {required_output_kind}, got {contract.output_kind}"
        )
    regression_conversion = None
    if contract.output_kind == "continuous_regression":
        regression_conversion = _load_regression_conversion(task_root)
    temporary = output_file.with_name(f".{output_file.name}.{uuid.uuid4().hex}.tmp")
    marker = output_file.with_suffix(output_file.suffix + ".complete")
    marker_tmp = marker.with_name(f".{marker.name}.{uuid.uuid4().hex}.tmp")
    try:
        with h5py.File(input_file, "r") as source, h5py.File(temporary, "x") as destination:
            raw = source["timeseries/channel0001/timeseries"]
            if raw.ndim != 1 or raw.dtype != np.dtype("int8"):
                raise ValueError("TIDMAD raw input must be a one-dimensional int8 stream")
            if raw.shape[0] % SEGMENT_SIZE:
                raise ValueError("raw input length is not divisible by the frozen segment size")
            group = destination.require_group("timeseries").create_group("channel0001")
            for name, value in source["timeseries/channel0001"].attrs.items():
                group.attrs[name] = value
            output = group.create_dataset(
                "timeseries",
                shape=raw.shape,
                dtype="int8",
                chunks=(SEGMENT_SIZE,),
            )
            segments = raw.shape[0] // SEGMENT_SIZE
            batch = contract.inference_batch_size
            for first in range(0, segments, batch):
                count = min(batch, segments - first)
                start = first * SEGMENT_SIZE
                stop = (first + count) * SEGMENT_SIZE
                raw_batch = np.asarray(raw[start:stop]).reshape(count, SEGMENT_SIZE)
                output[start:stop] = _decode(
                    model, raw_batch, device, contract, regression_conversion
                ).reshape(-1)
            destination.flush()
        os.replace(temporary, output_file)
        with marker_tmp.open("x") as handle:
            handle.write("complete\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(marker_tmp, marker)
    except BaseException:
        temporary.unlink(missing_ok=True)
        marker_tmp.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--input-file", type=Path, required=True)
    parser.add_argument("--output-file", type=Path, required=True)
    parser.add_argument("--task-root", type=Path)
    parser.add_argument("--required-output-kind", choices=("continuous_regression",))
    args = parser.parse_args()
    run_segment_model(
        candidate=args.candidate,
        input_file=args.input_file,
        output_file=args.output_file,
        task_root=args.task_root,
        required_output_kind=args.required_output_kind,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
