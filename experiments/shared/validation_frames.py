"""Bounded, deadline-aware framing for private local worker pipes."""

from __future__ import annotations

import os
import select
import struct
import time


def _ready(fd: int, *, write: bool, deadline: float) -> None:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("validation worker deadline exhausted")
    readable, writable, _ = select.select(
        [] if write else [fd], [fd] if write else [], [], remaining
    )
    if not (writable if write else readable):
        raise TimeoutError("validation worker deadline exhausted")


def _read(fd: int, count: int, *, deadline: float) -> bytes:
    result = bytearray()
    while len(result) < count:
        _ready(fd, write=False, deadline=deadline)
        try:
            block = os.read(fd, min(count - len(result), 1024 * 1024))
        except BlockingIOError:
            continue
        if not block:
            raise EOFError("validation worker frame truncated")
        result.extend(block)
    return bytes(result)


def read_frame(fd: int, *, max_bytes: int, deadline: float) -> bytes:
    size = struct.unpack("!Q", _read(fd, 8, deadline=deadline))[0]
    if size > max_bytes:
        raise ValueError("validation worker frame exceeds limit")
    return _read(fd, size, deadline=deadline)


def write_frame(fd: int, payload: bytes, *, max_bytes: int, deadline: float) -> None:
    if len(payload) > max_bytes:
        raise ValueError("validation worker frame exceeds limit")
    for data in (struct.pack("!Q", len(payload)), payload):
        view = memoryview(data)
        while view:
            _ready(fd, write=True, deadline=deadline)
            # PIPE_BUF-sized writes cannot block after select reports room for
            # a pipe writer. Large writes could defeat this absolute deadline.
            try:
                count = os.write(fd, view[:4096])
            except BlockingIOError:
                continue
            if count <= 0:
                raise EOFError("validation worker pipe closed")
            view = view[count:]
