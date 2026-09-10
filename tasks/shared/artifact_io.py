"""Task-package artifact I/O and integrity helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    """Return the experiment repository root from this module's location."""
    return Path(__file__).resolve().parents[2]


def examples_root(root: Path | None = None) -> Path:
    return (root or repo_root()) / "examples"


def dump_json_text(payload: Any) -> str:
    """Render stable, reviewable JSON with a trailing newline."""
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_text(path: Path, text: str) -> Path:
    """Write UTF-8 text with LF endings and return the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def write_json(path: Path, payload: Any) -> Path:
    return write_text(path, dump_json_text(payload))


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_of_file(path: Path) -> str:
    return sha256_of_bytes(path.read_bytes())


def render_sha256sums(pins: Mapping[str, str]) -> str:
    """Render sha256sum-compatible lines in stable name order."""
    return "".join(f"{pins[name]}  {name}\n" for name in sorted(pins))


def parse_sha256sums(text: str) -> dict[str, str]:
    """Parse sha256sum-compatible text, tolerating blank lines only."""
    pins: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        if len(digest) != 64 or not name:
            raise ValueError(f"malformed SHA256SUMS line: {raw!r}")
        pins[name] = digest
    return pins


def write_sha256sums(directory: Path, names: Iterable[str]) -> dict[str, str]:
    """Pin named files below a directory and write its SHA256SUMS file."""
    pins = {name: sha256_of_file(directory / name) for name in names}
    write_text(directory / "SHA256SUMS", render_sha256sums(pins))
    return pins
