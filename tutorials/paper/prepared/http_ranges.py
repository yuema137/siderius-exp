"""Read bounded HDF5 byte ranges without downloading an entire raw shard."""

from __future__ import annotations

import io
import urllib.request
from collections import OrderedDict


class HTTPRangeReader(io.RawIOBase):
    """Seekable, bounded block cache; reject servers that ignore Range requests."""

    def __init__(self, url: str, size: int, *, block_size: int = 1 << 20):
        self.url, self.size, self.block_size = url, size, block_size
        self.position = 0
        self.blocks: OrderedDict[int, bytes] = OrderedDict()
        self.downloaded_bytes = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        position = offset + (
            0 if whence == 0 else self.position if whence == 1 else self.size
        )
        if whence not in (0, 1, 2) or position < 0:
            raise ValueError("invalid seek")
        self.position = position
        return position

    def _block(self, index: int) -> bytes:
        if index in self.blocks:
            self.blocks.move_to_end(index)
            return self.blocks[index]
        start = index * self.block_size
        end = min(start + self.block_size, self.size) - 1
        request = urllib.request.Request(
            self.url,
            headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"},
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            expected = f"bytes {start}-{end}/{self.size}"
            if (
                response.status != 206
                or response.headers.get("Content-Range") != expected
            ):
                raise ValueError(
                    "Data server did not honor the exact byte range; refusing a full-file download."
                )
            data = response.read(end - start + 2)
        if len(data) != end - start + 1:
            raise ValueError(
                "incomplete data range; retry preparation with a new dataset name"
            )
        self.downloaded_bytes += len(data)
        self.blocks[index] = data
        while len(self.blocks) > 32:
            self.blocks.popitem(last=False)
        return data

    def read(self, size=-1):
        stop = self.size if size < 0 else min(self.size, self.position + size)
        chunks = []
        while self.position < stop:
            index, offset = divmod(self.position, self.block_size)
            block = self._block(index)
            chunk = block[offset : offset + stop - self.position]
            chunks.append(chunk)
            self.position += len(chunk)
        return b"".join(chunks)

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)
