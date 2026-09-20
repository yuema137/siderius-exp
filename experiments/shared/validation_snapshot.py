"""Ephemeral, sealed numeric state for Linux validation workers.

The launcher passes the descriptor to an already-confined worker. Possession
does not certify training or authorize private validation. Never deserialize
candidate state in the private-data coordinator.
"""

import ctypes
import fcntl
import os
import stat
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass

import torch


def _create_memfd() -> int:
    # Some managed CPython builds omit os.memfd_create on supported kernels.
    create = ctypes.CDLL(None, use_errno=True).memfd_create
    create.argtypes = [ctypes.c_char_p, ctypes.c_uint]
    create.restype = ctypes.c_int
    descriptor = create(b"validation-state", 0x0001 | 0x0002)
    if descriptor < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return descriptor


@dataclass(frozen=True)
class SealedState:
    """Borrowed descriptor, valid only during the owning context."""

    fd: int
    size_bytes: int


def validate_sealed_snapshot(descriptor: int, *, max_bytes: int) -> int:
    """Validate a received snapshot without deserializing it."""
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= max_bytes:
        raise ValueError("snapshot type or size is invalid")
    if fcntl.fcntl(descriptor, 1034) & 0x000F != 0x000F:
        raise ValueError("snapshot is not immutable")
    return info.st_size


def load_worker_snapshot(descriptor: int, *, max_bytes: int) -> dict[str, torch.Tensor]:
    """Only call inside the confined worker, never a private-data coordinator."""
    validate_sealed_snapshot(descriptor, max_bytes=max_bytes)
    with os.fdopen(os.dup(descriptor), "rb") as stream:
        stream.seek(0)
        state = torch.load(stream, map_location="cpu", weights_only=True)
    if type(state) is not dict or any(
        type(name) is not str
        or type(value) is not torch.Tensor
        or value.layout != torch.strided
        for name, value in state.items()
    ):
        raise TypeError("snapshot requires a plain dictionary of dense tensors")
    return state


@contextmanager
def sealed_tensor_state(
    state: Mapping[str, torch.Tensor], *, max_tensor_bytes: int
) -> Iterator[SealedState]:
    """Copy plain dense state to immutable RAM without a durable checkpoint.

    The caller quiesces optimizer updates while taking the snapshot. The byte
    limit bounds raw tensor payload, not serialization metadata or total RSS.
    GPU state is copied to CPU; the worker uses weights_only=True and strict
    state restoration. No arbitrary module objects or tensor subclasses enter
    this representation. Do not use it to replace formal checkpoint storage.
    """
    if type(max_tensor_bytes) is not int or max_tensor_bytes < 0:
        raise ValueError("max_tensor_bytes must be a nonnegative integer")
    items = list(state.items())
    total = 0
    for name, tensor in items:
        if type(name) is not str or type(tensor) is not torch.Tensor:
            raise TypeError("state requires string keys and plain tensors")
        if tensor.layout != torch.strided or tensor.device.type == "meta":
            raise ValueError("state requires materialized dense tensors")
        total += tensor.numel() * tensor.element_size()
        if total > max_tensor_bytes:
            raise ValueError("state exceeds tensor byte limit")
    descriptor = _create_memfd()
    try:
        numeric = {
            name: tensor.detach().to(device="cpu", copy=True).contiguous()
            for name, tensor in items
        }
        with os.fdopen(os.dup(descriptor), "wb") as stream:
            torch.save(numeric, stream)
        del numeric
        # Linux UAPI linux/fcntl.h: F_ADD_SEALS=1024+9, the four seals=0xf.
        # The same managed builds can omit these Python constants as well.
        fcntl.fcntl(descriptor, 1033, 0x000F)
        os.lseek(descriptor, 0, os.SEEK_SET)
        yield SealedState(descriptor, os.fstat(descriptor).st_size)
    finally:
        os.close(descriptor)
