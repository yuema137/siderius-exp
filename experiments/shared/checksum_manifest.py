"""Verify caller-selected files against a repository-owned SHA-256 manifest."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

_ENTRY = re.compile(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)\Z")


def sha256_file(path: Path) -> str:
    """Hash a file without loading a dataset into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def declared_checksums(manifest: Path, names: set[str]) -> dict[str, str]:
    """Require exactly one valid checksum entry for each selected basename."""

    entries: dict[str, str] = {}
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        match = _ENTRY.fullmatch(line)
        if match is None:
            raise ValueError(f"invalid checksum manifest line {number}: {manifest}")
        digest, name = match.groups()
        if name in entries:
            raise ValueError(f"duplicate checksum entry: {name}")
        entries[name] = digest
    missing = names - entries.keys()
    if missing:
        raise ValueError(f"checksum manifest lacks selected files: {sorted(missing)}")
    return {name: entries[name] for name in sorted(names)}


def verify_selected_files(root: Path, manifest: Path, names: set[str]) -> dict[str, str]:
    """Require every selected file to exist and match its frozen digest."""

    if not root.is_dir():
        raise ValueError(f"data directory is missing: {root}")
    checksums = declared_checksums(manifest, names)
    for name, expected in checksums.items():
        path = root / name
        if not path.is_file():
            raise ValueError(f"selected data file is missing: {path}")
        if sha256_file(path) != expected:
            raise ValueError(f"selected data checksum mismatch: {path}")
    return checksums
