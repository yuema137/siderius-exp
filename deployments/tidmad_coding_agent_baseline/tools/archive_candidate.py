"""Publish one validly scored candidate as an immutable directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .io import atomic_write_json, fsync_directory, fsync_tree, sha256_file
from .model import BANDS, DEVELOPMENT_FILE_BY_BAND

_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_REQUIRED = ("architecture.json", "train_config.json", "weights.pth", "predict.py")


def validate_candidate_identity(candidate_id: str) -> None:
    """Refuse identities that cannot safely become evaluator-owned paths."""

    if not _IDENTITY.fullmatch(candidate_id):
        raise ValueError(f"invalid candidate identity: {candidate_id!r}")


def validate_candidate_source(source: Path) -> None:
    """Refuse incomplete, transient, data-bearing, or linked candidate trees."""

    if not source.is_dir():
        raise ValueError(f"candidate source is not a directory: {source}")
    for name in _REQUIRED:
        if not (source / name).is_file():
            raise ValueError(f"candidate source is missing {name}")
    if not (source / "model.py").is_file() and not (source / "model").is_dir():
        raise ValueError("candidate source needs model.py or a model/ source directory")
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"candidate source contains a symlink: {path}")
        if path.is_file() and (path.name.endswith(".tmp") or path.suffix in {".h5", ".hdf5"}):
            raise ValueError(f"candidate source contains a temporary/data artifact: {path}")


def _validate_score(path: Path, band: str, expected_candidate_digest: str) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    scalar = payload.get("scalar")
    vector = payload.get("file_vector")
    if payload.get("valid") is not True:
        raise ValueError("only a validly scored candidate may be archived")
    if not isinstance(scalar, (float, int)) or not math.isfinite(float(scalar)):
        raise ValueError("score scalar must be finite")
    if not isinstance(vector, list) or len(vector) != 20:
        raise ValueError("score file_vector must have exactly 20 entries")
    expected = {DEVELOPMENT_FILE_BY_BAND[band]}
    present = {index for index, value in enumerate(vector) if value is not None}
    if present != expected:
        raise ValueError(
            "development score vector identities "
            f"{sorted(present)} differ from frozen holdout for band {band}"
        )
    if payload.get("candidate_tree_sha256") != expected_candidate_digest:
        raise ValueError("score is not bound to these candidate bytes")
    return payload


def _manifest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def candidate_tree_digest(root: Path) -> str:
    """Hash the exact candidate-file manifest using a stable encoding."""

    payload = json.dumps(_manifest(root), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _seal_tree(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        path.chmod(0o550 if path.is_dir() else 0o440)
    root.chmod(0o550)


def archive_candidate(
    *, source: Path, score_path: Path, archive_root: Path, band: str, candidate_id: str
) -> Path:
    if band not in BANDS:
        raise ValueError(f"unsupported band: {band}")
    validate_candidate_identity(candidate_id)
    validate_candidate_source(source)
    digest = candidate_tree_digest(source)
    score = _validate_score(score_path, band, digest)
    band_root = archive_root / band
    band_root.mkdir(parents=True, exist_ok=True)
    destination = band_root / candidate_id
    if destination.exists():
        raise FileExistsError(f"candidate already published: {destination}")

    temporary = Path(tempfile.mkdtemp(prefix=f".{candidate_id}.", dir=band_root))
    try:
        shutil.copytree(source, temporary / "candidate", dirs_exist_ok=True)
        if candidate_tree_digest(temporary / "candidate") != digest:
            raise RuntimeError("candidate bytes changed while they were being archived")
        shutil.copy2(score_path, temporary / "score.json")
        files = _manifest(temporary)
        atomic_write_json(
            temporary / "candidate_manifest.json",
            {
                "version": "tidmad-coding-agent-candidate-v1",
                "candidate_id": candidate_id,
                "band": band,
                "scalar": float(score["scalar"]),
                "selection_split": "development",
                "candidate_tree_sha256": digest,
                "files": files,
            },
        )
        atomic_write_json(temporary / "COMPLETE.json", {"complete": True})
        _seal_tree(temporary)
        fsync_tree(temporary)
        os.rename(temporary, destination)
        fsync_directory(band_root)
        _update_best(archive_root, band, candidate_id, float(score["scalar"]))
        return destination
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _update_best(archive_root: Path, band: str, candidate_id: str, scalar: float) -> None:
    marker = archive_root / "best" / f"{band}.json"
    if marker.exists():
        current = json.loads(marker.read_text())
        if float(current["scalar"]) >= scalar:
            return
    atomic_write_json(
        marker,
        {"band": band, "candidate_id": candidate_id, "scalar": scalar},
    )
    marker.chmod(0o440)
    fsync_directory(marker.parent)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--archive-root", type=Path, default=Path("/work/state/candidates"))
    parser.add_argument("--band", choices=BANDS, required=True)
    parser.add_argument("--candidate-id", required=True)
    args = parser.parse_args()
    print(
        archive_candidate(
            source=args.source,
            score_path=args.score,
            archive_root=args.archive_root,
            band=args.band,
            candidate_id=args.candidate_id,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
