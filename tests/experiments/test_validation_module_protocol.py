"""Numeric wire values and bounded pipe framing; no scientific data."""

import os
import struct
import sys
import threading
import time

import pytest
import torch

from experiments.shared.validation_frames import read_frame, write_frame
from experiments.shared.validation_module_peer import ModulePeer
from experiments.shared.validation_module_protocol import (
    ModuleCall,
    ModuleResult,
    TensorPayload,
)
from experiments.shared.validation_rng import (
    capture_validation_rng,
    restore_validation_rng,
)


@pytest.mark.parametrize(
    "value",
    [
        torch.tensor(2.5),
        torch.arange(12, dtype=torch.float32).reshape(3, 4).T,
        torch.tensor([1.25, -0.5], dtype=torch.bfloat16),
        torch.tensor([True, False]),
        torch.tensor([complex(1, 2)], dtype=torch.complex64).conj(),
        torch.tensor([float("nan"), float("inf")]),
        torch.empty((2, 0, 4)),
        torch.tensor([2**40], dtype=torch.int64),
    ],
)
def test_tensor_roundtrip_preserves_dtype_shape_and_values(value):
    encoded = TensorPayload.capture(value)
    received = TensorPayload.model_validate_json(encoded.model_dump_json())
    actual = received.tensor(device=torch.device("cpu"))
    torch.testing.assert_close(actual, value, rtol=0, atol=0, equal_nan=True)


@pytest.mark.parametrize(
    "change",
    [
        {"dtype": "object"},
        {"shape": [2]},
        {"shape": [-1]},
        {"shape": [True]},
        {"byteorder": "big" if sys.byteorder == "little" else "little"},
        {"data": b"truncated"},
        {"path": "/private/targets"},
    ],
)
def test_tensor_refuses_inconsistent_or_executable_representation(change):
    original = TensorPayload.capture(torch.tensor(1.0)).model_dump()
    with pytest.raises(ValueError):
        TensorPayload.model_validate({**original, **change})


def test_sparse_tensor_is_refused_instead_of_silently_changing_representation():
    with pytest.raises(ValueError, match="dense"):
        TensorPayload.capture(torch.eye(2).to_sparse())


@pytest.mark.parametrize("case", ["oversize", "truncated", "stalled"])
def test_pipe_frame_is_bounded_by_length_and_original_deadline(case):
    reader, writer = os.pipe()
    try:
        if case == "oversize":
            os.write(writer, struct.pack("!Q", 2**40))
            expected = ValueError
        else:
            os.write(writer, struct.pack("!Q", 100) + b"partial")
            expected = EOFError if case == "truncated" else TimeoutError
        if case == "truncated":
            os.close(writer)
            writer = None
        started = time.monotonic()
        with pytest.raises(expected):
            read_frame(reader, max_bytes=1024, deadline=started + 0.1)
        assert time.monotonic() - started < 2
    finally:
        os.close(reader)
        if writer is not None:
            os.close(writer)


def test_stalled_pipe_writer_obeys_absolute_deadline():
    reader, writer = os.pipe()
    try:
        started = time.monotonic()
        with pytest.raises(TimeoutError):
            write_frame(
                writer, b"x" * 1024**2, max_bytes=2 * 1024**2, deadline=started + 0.1
            )
        assert time.monotonic() - started < 2
    finally:
        os.close(reader)
        os.close(writer)


@pytest.mark.parametrize("wrong", ["sequence", "operation"])
def test_response_identity_is_checked_before_restoring_rng(wrong):
    original = capture_validation_rng()
    torch.rand(1)
    different = capture_validation_rng()
    restore_validation_rng(original)
    request_read, request_write = os.pipe()
    response_read, response_write = os.pipe()
    deadline = time.monotonic() + 3
    failures = []

    def fake_worker():
        try:
            request = ModuleCall.model_validate_json(
                read_frame(request_read, max_bytes=65536, deadline=deadline)
            )
            response = ModuleResult(
                sequence=request.sequence + (wrong == "sequence"),
                operation="mode" if wrong == "operation" else request.operation,
                rng=different,
                training=True,
            )
            write_frame(
                response_write,
                response.model_dump_json().encode(),
                max_bytes=65536,
                deadline=deadline,
            )
        except (ValueError, OSError, EOFError, RuntimeError) as exc:
            failures.append(exc)

    thread = threading.Thread(target=fake_worker)
    thread.start()
    try:
        with pytest.raises(ValueError, match="response identity mismatch"):
            ModulePeer(
                input_fd=request_write,
                output_fd=response_read,
                device=torch.device("cpu"),
                deadline=deadline,
                max_frame_bytes=65536,
            )
        assert capture_validation_rng() == original
    finally:
        thread.join(timeout=4)
        for fd in (request_read, request_write, response_read, response_write):
            os.close(fd)
        restore_validation_rng(original)
    assert not thread.is_alive() and not failures
