"""Shared fetch, verification, and extraction mechanics for task data tools."""

from __future__ import annotations

import hashlib
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArchiveSpec:
    """One official artifact and its byte identity."""

    name: str
    url: str
    sha256: str
    extract_member_dir: str


class ArchiveIntegrityError(RuntimeError):
    """An archive's bytes or extracted layout differ from the declaration."""


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_or_fetch(
    dest: Path, spec: ArchiveSpec, *, allow_download: bool = True
) -> Path:
    """Return the verified archive, downloading a missing artifact when allowed."""
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / spec.name
    if not target.exists():
        if not allow_download:
            raise FileNotFoundError(
                f"{target} is absent and --no-download was given; fetch it from "
                f"{spec.url} (official source) or drop the flag."
            )
        print(f"[fetch] {spec.url} -> {target}")
        with urllib.request.urlopen(spec.url) as response, target.open("wb") as output:
            while chunk := response.read(1 << 20):
                output.write(chunk)
    actual = sha256_of_file(target)
    if actual != spec.sha256:
        raise ArchiveIntegrityError(
            f"{target.name}: sha256 {actual} does not match the pinned "
            f"{spec.sha256}. Refusing to proceed — delete the file and re-fetch "
            f"from the official source ({spec.url}) if it is corrupt."
        )
    print(f"[verified] {target.name} sha256={actual}")
    return target


def extract_archive(dest: Path, spec: ArchiveSpec) -> Path:
    """Extract a verified tar.gz or zip archive, checking its declared layout."""
    member_dir = dest / spec.extract_member_dir
    if member_dir.is_dir():
        print(f"[skip-extract] {member_dir} already exists")
        return member_dir
    archive = dest / spec.name
    print(f"[extract] {archive.name} -> {member_dir}")
    if spec.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zip_file:
            zip_file.extractall(dest)
    else:
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(dest, filter="data")
    if not member_dir.is_dir():
        raise ArchiveIntegrityError(
            f"extraction of {archive.name} did not produce {member_dir} — the "
            "archive layout differs from the official distribution."
        )
    return member_dir


def require_out_of_tree(dest: Path, repository_root: Path, error) -> Path:
    """Refuse a data destination inside the experiment repository."""
    resolved = dest.resolve()
    if resolved.is_relative_to(repository_root):
        error(
            f"--dest {resolved} is inside the repository; the task lifecycle "
            "requires a machine-local directory outside the tree."
        )
    return resolved
