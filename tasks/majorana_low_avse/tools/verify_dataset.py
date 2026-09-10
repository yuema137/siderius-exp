"""Verify the official Majorana Zenodo partial release against its manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--supervised-only", action="store_true")
    args = parser.parse_args()
    entries = json.loads(args.manifest.read_text(encoding="utf-8"))["files"]
    checked = 0
    for name, expected in entries.items():
        if args.supervised_only and expected["role"] == "unlabeled":
            continue
        path = args.data_dir / name
        if not path.is_file():
            raise SystemExit(f"dataset verification refused: missing {name}")
        actual_size = path.stat().st_size
        if actual_size != expected["bytes"]:
            raise SystemExit(
                f"dataset verification refused: {name} has {actual_size} bytes; "
                f"expected {expected['bytes']}"
            )
        actual_md5 = _md5(path)
        if actual_md5 != expected["md5"]:
            raise SystemExit(
                f"dataset verification refused: {name} MD5 {actual_md5}; "
                f"expected {expected['md5']}"
            )
        checked += 1
    print(f"Majorana dataset verification passed: {checked} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
