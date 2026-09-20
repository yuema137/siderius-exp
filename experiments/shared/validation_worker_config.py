"""Read one bounded worker config, by legacy path or inherited read descriptor.

The protected launcher may keep diagnostic files owner-only and outside worker
mounts. Descriptor inheritance grants access to this config alone; it does not
authenticate a researcher invoking the CLI independently.
"""

import argparse
import os
from pathlib import Path


def read_worker_config(*, description: str | None) -> bytes:
    parser = argparse.ArgumentParser(description=description)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--config", type=Path)
    source.add_argument("--config-fd", type=int)
    args = parser.parse_args()
    with (
        args.config.open("rb")
        if args.config is not None
        else os.fdopen(args.config_fd, "rb")
    ) as stream:
        payload = stream.read(4194305)
    if len(payload) > 4194304:
        raise ValueError("worker configuration exceeds limit")
    return payload
