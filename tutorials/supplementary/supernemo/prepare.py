"""Prepare external event indexes with the unchanged scientific task profiler."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from tutorials.shared.runtime import ROOT, disjoint

TASK = ROOT / "tasks/supernemo_signal_background"
SOURCE_MANIFEST = TASK / "declared/source_files.json"
PROFILER = TASK / "tools/profile_dataset.py"
RECEIPT = "preparation.json"
PROCESSES = ("0nubb", "2nubb", "Bi214", "Tl208")


class FileEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bytes: int = Field(gt=0)
    md5: str = Field(pattern=r"^[0-9a-f]{32}$")


class SourceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record: int
    doi: str
    files: dict[str, FileEntry]


class RawBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: str
    bytes: int
    mtime_ns: int
    md5: str


class PreparationReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["supernemo-preparation-v1"] = "supernemo-preparation-v1"
    source_manifest_sha256: str
    profiler_sha256: str
    raw_files: dict[str, RawBinding]
    generated_sha256: dict[str, str]


def digest(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm, usedforsecurity=False)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def raw_bindings(raw: Path, *, hashes: bool) -> dict[str, RawBinding]:
    manifest = SourceManifest.model_validate_json(SOURCE_MANIFEST.read_text())
    result = {}
    for filename, declared in manifest.files.items():
        path = raw / filename
        if not path.is_file():
            raise ValueError(f"Missing official raw file: {path}")
        stat = path.stat()
        if stat.st_size != declared.bytes:
            raise ValueError(
                f"Official byte size differs: {path}; restore the download"
            )
        if hashes and digest(path, "md5") != declared.md5:
            raise ValueError(f"Official MD5 differs: {path}; restore the download")
        result[filename] = RawBinding(
            target=str(path.resolve()),
            bytes=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            md5=declared.md5,
        )
    return result


def generated_paths(root: Path) -> list[Path]:
    return [
        *(root / "event_indexes" / f"{p}_event_index.npz" for p in PROCESSES),
        root / "event_indexes/dataset_profile.json",
    ]


def verify_prepared(root: Path, *, hashes: bool = False) -> PreparationReceipt:
    """Hash indexes every time; full raw MD5 is explicit and required at launch."""
    receipt_path = root / RECEIPT
    if not receipt_path.is_file() or (root / ".incomplete").exists():
        raise ValueError(
            f"Incomplete SuperNEMO preparation: {root}; prepare a new directory"
        )
    receipt = PreparationReceipt.model_validate_json(receipt_path.read_text())
    if receipt.source_manifest_sha256 != digest(
        SOURCE_MANIFEST
    ) or receipt.profiler_sha256 != digest(PROFILER):
        raise ValueError("Preparation source identity changed; prepare a new directory")
    expected = {str(p.relative_to(root)) for p in generated_paths(root)}
    if set(receipt.generated_sha256) != expected:
        raise ValueError(
            "Preparation receipt does not name the complete index/report set"
        )
    bindings = raw_bindings(root, hashes=hashes)
    if bindings != receipt.raw_files:
        raise ValueError(
            "Prepared raw-file bindings changed; restore them or prepare a new directory"
        )
    for relative, expected_digest in receipt.generated_sha256.items():
        if digest(root / relative) != expected_digest:
            raise ValueError(
                f"Prepared index/report changed: {relative}; prepare a new directory"
            )
    return receipt


def require_external_output(path: Path, prepared: Path) -> None:
    """Keep user inputs/results outside the original raw parents behind the links."""
    receipt_path = prepared / RECEIPT
    if not receipt_path.is_file():
        raise ValueError(
            "Missing preparation.json. Run python -m tutorials.supplementary.supernemo.prepare "
            "--raw-data-dir /absolute/raw --output-dir /absolute/prepared, then use the prepared directory."
        )
    receipt = PreparationReceipt.model_validate_json(receipt_path.read_text())
    actual = raw_bindings(prepared, hashes=False)
    if actual != receipt.raw_files:
        raise ValueError(
            "Prepared raw-file bindings changed; restore them before initialization"
        )
    if any(
        not disjoint(path, Path(binding.target).parent) for binding in actual.values()
    ):
        raise ValueError(
            "Project and run output must be separate from original raw-data directories"
        )


def prepare(raw: Path, output: Path) -> Path:
    raw, output = raw.resolve(), output.resolve()
    if (
        not disjoint(raw, ROOT)
        or not disjoint(output, ROOT)
        or not disjoint(raw, output)
    ):
        raise ValueError(
            "Raw and prepared directories must be separate and outside the exp checkout"
        )
    if output.exists():
        raise ValueError(
            "Choose a new preparation directory; existing indexes are never overwritten"
        )
    bindings = raw_bindings(raw, hashes=True)
    output.mkdir(parents=True)
    incomplete = output / ".incomplete"
    incomplete.write_text(
        "Preparation has not completed; do not launch from this directory.\n"
    )
    for name, binding in bindings.items():
        (output / name).symlink_to(binding.target)
    indexes = output / "event_indexes"
    indexes.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-B",
            str(PROFILER),
            "--data-dir",
            str(output),
            "--output-dir",
            str(indexes),
        ],
        check=True,
    )
    if raw_bindings(output, hashes=False) != bindings:
        raise ValueError(
            "Raw files changed during preparation; retain evidence and start fresh"
        )
    receipt = PreparationReceipt(
        source_manifest_sha256=digest(SOURCE_MANIFEST),
        profiler_sha256=digest(PROFILER),
        raw_files=bindings,
        generated_sha256={
            str(p.relative_to(output)): digest(p) for p in generated_paths(output)
        },
    )
    destination = output / RECEIPT
    with destination.open("x") as stream:
        stream.write(receipt.model_dump_json(indent=2) + "\n")
    incomplete.unlink()
    verify_prepared(output)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-data-dir", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        receipt = verify_prepared(args.output_dir.resolve(), hashes=True)
        print(
            f"Verified {len(receipt.raw_files)} official files and all event indexes."
        )
    else:
        if args.raw_data_dir is None:
            parser.error("--raw-data-dir is required for preparation")
        print(f"Preparation receipt: {prepare(args.raw_data_dir, args.output_dir)}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(f"SuperNEMO preparation refused: {error}")
