"""Numeric-only messages between a private coordinator and confined workers.

No pickle, candidate source, filesystem path or deployment authority is accepted
by these per-call messages. Size/deadline enforcement belongs to the framing
layer; the decoder checks shape/dtype/byte agreement before tensor allocation.
"""

from __future__ import annotations

import math
import sys
from typing import Annotated, Literal

import torch
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    model_validator,
)

from experiments.shared.validation_rng import ValidationRngState

_DTYPES = {
    name: getattr(torch, name)
    for name in (
        "bool",
        "uint8",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint16",
        "uint32",
        "uint64",
        "float16",
        "bfloat16",
        "float32",
        "float64",
        "complex64",
        "complex128",
    )
}
_WIDTHS = {
    name: torch.empty((), dtype=dtype).element_size() for name, dtype in _DTYPES.items()
}


class Message(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", ser_json_bytes="base64", val_json_bytes="base64"
    )


class TensorPayload(Message):
    dtype: str
    shape: Annotated[
        tuple[Annotated[StrictInt, Field(ge=0)], ...], Field(max_length=64)
    ]
    byteorder: Literal["little", "big"]
    data: bytes

    @model_validator(mode="after")
    def consistent(self) -> TensorPayload:
        if self.dtype not in _DTYPES:
            raise ValueError("unsupported tensor dtype")
        if self.byteorder != sys.byteorder:
            raise ValueError("tensor byte order mismatch")
        if math.prod(self.shape) * _WIDTHS[self.dtype] != len(self.data):
            raise ValueError("tensor shape/dtype/byte count mismatch")
        return self

    @classmethod
    def capture(cls, value: torch.Tensor) -> TensorPayload:
        if (
            type(value) is not torch.Tensor
            or value.layout != torch.strided
            or value.is_quantized
        ):
            raise ValueError(
                "validation transport requires dense, unquantized base tensors"
            )
        values = value.detach().resolve_conj().resolve_neg().cpu().contiguous()
        return cls(
            dtype=str(values.dtype).removeprefix("torch."),
            shape=tuple(values.shape),
            byteorder=sys.byteorder,
            data=values.reshape(-1).view(torch.uint8).numpy().tobytes(),
        )

    def tensor(self, *, device: torch.device) -> torch.Tensor:
        dtype = _DTYPES[self.dtype]
        if not self.data:
            return torch.empty(self.shape, dtype=dtype, device=device)
        return (
            torch.frombuffer(bytearray(self.data), dtype=dtype)
            .reshape(self.shape)
            .to(device)
        )


Operation = Literal["forward", "state", "mode", "describe"]


class ModuleCall(Message):
    sequence: Annotated[StrictInt, Field(ge=0)]
    operation: Operation
    rng: ValidationRngState
    inputs: Annotated[tuple[TensorPayload, ...], Field(max_length=2)] = ()
    training: StrictBool | None = None

    @model_validator(mode="after")
    def operation_fields(self) -> ModuleCall:
        if self.operation == "forward":
            if not self.inputs or self.training is not None:
                raise ValueError("forward requires inputs only")
        elif self.inputs or (self.training is not None) != (self.operation == "mode"):
            raise ValueError("mode/state fields do not match operation")
        return self


class ModuleResult(Message):
    sequence: Annotated[StrictInt, Field(ge=0)]
    operation: Operation
    status: Literal["ok"] = "ok"
    rng: ValidationRngState
    training: StrictBool
    output: TensorPayload | None = None
    state: dict[str, TensorPayload] | None = None

    @model_validator(mode="after")
    def result_fields(self) -> ModuleResult:
        if (self.output is not None) != (self.operation == "forward"):
            raise ValueError("output does not match operation")
        if (self.state is not None) != (self.operation == "state"):
            raise ValueError("state does not match operation")
        return self


class ModuleFailure(Message):
    status: Literal["refused"] = "refused"
    code: Literal[
        "invalid_request", "execution_failed", "deadline_exhausted", "startup_failed"
    ]
