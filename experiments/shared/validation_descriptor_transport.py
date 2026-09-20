"""Transfer sealed snapshot descriptors over an inherited Unix stream socket.

The receiver owns returned descriptors and must close them. It inspects seals
and size without deserializing tensors; only a confined numeric worker loads
the checkpoint. No pathname or listening socket is involved.
"""

import array
import os
import socket
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from experiments.shared.validation_frames import read_frame, write_frame
from experiments.shared.validation_snapshot import validate_sealed_snapshot


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("validation descriptor deadline exhausted")
    return remaining


def send_snapshots(
    channel: socket.socket,
    metadata: bytes,
    descriptors: Sequence[int],
    *,
    deadline: float,
    max_metadata_bytes: int,
) -> None:
    if len(descriptors) != 2:
        raise ValueError("an epoch requires model and objective snapshots")
    if len(metadata) > max_metadata_bytes:
        raise ValueError("epoch metadata exceeds limit")
    previous = channel.gettimeout()
    try:
        channel.settimeout(_remaining(deadline))
        count = channel.sendmsg(
            [b"S"],
            [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", descriptors))],
        )
        if count != 1:
            raise EOFError("snapshot descriptor transfer failed")
        write_frame(
            channel.fileno(), metadata, max_bytes=max_metadata_bytes, deadline=deadline
        )
    finally:
        channel.settimeout(previous)


@contextmanager
def receive_snapshots(
    channel: socket.socket,
    *,
    deadline: float,
    max_metadata_bytes: int,
    max_snapshot_bytes: int,
) -> Iterator[tuple[bytes, tuple[int, int]]]:
    """Close every received descriptor on success, malformed input or timeout."""
    descriptors: list[int] = []
    previous = channel.gettimeout()
    try:
        channel.settimeout(_remaining(deadline))
        width = array.array("i").itemsize
        marker, ancillary, flags, _ = channel.recvmsg(
            1, socket.CMSG_SPACE(2 * width), socket.MSG_CMSG_CLOEXEC
        )
        invalid = False
        for level, kind, data in ancillary:
            if level != socket.SOL_SOCKET or kind != socket.SCM_RIGHTS:
                invalid = True
                continue
            values = array.array("i")
            values.frombytes(data[: len(data) - len(data) % width])
            descriptors.extend(values)
            invalid |= bool(len(data) % width)
        if (
            invalid
            or marker != b"S"
            or len(descriptors) != 2
            or flags & (socket.MSG_CTRUNC | socket.MSG_TRUNC)
        ):
            raise ValueError("invalid epoch snapshot descriptor message")
        for descriptor in descriptors:
            validate_sealed_snapshot(descriptor, max_bytes=max_snapshot_bytes)
        payload = read_frame(
            channel.fileno(), max_bytes=max_metadata_bytes, deadline=deadline
        )
        yield payload, (descriptors[0], descriptors[1])
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
        channel.settimeout(previous)
