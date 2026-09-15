"""Collect immutable winners without inventing missing scientific results."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from .io import atomic_write_json, fsync_directory, sha256_file
from .model import BANDS, utc_text
from .usage import aggregate_usage


def _tree_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _candidate(archive_root: Path, band: str, candidate_id: str) -> Path:
    path = archive_root / band / candidate_id
    if not (path / "COMPLETE.json").is_file():
        raise ValueError(f"winner is not a complete retained candidate: {path}")
    manifest_path = path / "candidate_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for relative, expected in manifest["files"].items():
        target = path / relative
        if not target.is_file() or sha256_file(target) != expected:
            raise ValueError(f"winner candidate file differs from manifest: {target}")
    return path


def _read_best(archive_root: Path) -> dict[str, tuple[str, Path]]:
    winners: dict[str, tuple[str, Path]] = {}
    for band in BANDS:
        marker = archive_root / "best" / f"{band}.json"
        if not marker.is_file():
            continue
        payload = json.loads(marker.read_text())
        candidate_id = str(payload["candidate_id"])
        winners[band] = (candidate_id, _candidate(archive_root, band, candidate_id))
    return winners


def _validated_final_score(
    path: Path, winners: dict[str, tuple[str, Path]]
) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text())
    expected = {band: identity for band, (identity, _) in winners.items()}
    if payload.get("valid") is not True:
        raise ValueError("final score record is not valid")
    if payload.get("winner_candidates") != expected:
        raise ValueError("final score was not produced from the marked band winners")
    vector = payload.get("file_vector")
    if (
        not isinstance(vector, list)
        or len(vector) != 20
        or any(value is None for value in vector)
    ):
        raise ValueError("final score record needs all 20 per-file values")
    return payload


def finalize(
    work_root: Path,
    product: str,
    archive_root: Path = Path("/var/lib/tidmad-baseline/candidates"),
    final_score_path: Path = Path("/var/lib/tidmad-baseline/final_score.json"),
) -> Path:
    winners = _read_best(archive_root)
    final_score = _validated_final_score(final_score_path, winners)
    submission = work_root / "submission"
    if submission.exists() and any(submission.iterdir()):
        raise FileExistsError(f"submission directory is not empty: {submission}")
    submission.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".submission.", dir=submission.parent))
    try:
        for band, (_, candidate) in winners.items():
            band_output = temporary / f"band_{band}"
            shutil.copytree(candidate / "candidate", band_output)
            band_output.chmod(0o750)
            shutil.copy2(candidate / "score.json", band_output / "score.json")
            (band_output / "score.json").chmod(0o440)
            band_output.chmod(0o550)
        if final_score is not None:
            atomic_write_json(temporary / "score_vector.json", final_score)
        receipts = work_root / "state" / "invocations.jsonl"
        invocation_count = (
            sum(1 for _ in receipts.open("rb")) if receipts.exists() else 0
        )
        complete = len(winners) == len(BANDS) and final_score is not None
        ended = int(time.time())
        start_path = work_root / "state" / "run_start.json"
        start = json.loads(start_path.read_text()) if start_path.is_file() else {}
        started = start.get("actual_start_epoch")
        atomic_write_json(
            temporary / "manifest.json",
            {
                "version": "tidmad-coding-agent-submission-v1",
                "product": product,
                "complete": complete,
                "winner_candidates": {
                    band: identity for band, (identity, _) in winners.items()
                },
                "missing_bands": [band for band in BANDS if band not in winners],
                "final_score_present": final_score is not None,
                "outer_loop_invocations": invocation_count,
                "scheduled_start_utc": start.get("scheduled_start_utc"),
                "actual_start_utc": start.get("actual_start_utc"),
                "actual_end_utc": utc_text(ended),
                "actual_wall_clock_seconds": (
                    ended - int(started) if isinstance(started, int) else None
                ),
                "gpu_hours": (
                    (ended - int(started)) / 3600 if isinstance(started, int) else None
                ),
                "token_usage": aggregate_usage(work_root / "logs", product),
                "work_tree_bytes": _tree_bytes(work_root),
                "retained_candidate_bytes": _tree_bytes(archive_root),
            },
        )
        atomic_write_json(temporary / "COMPLETE.json", {"complete": complete})
        if submission.exists():
            submission.rmdir()
        os.rename(temporary, submission)
        fsync_directory(submission.parent)
        return submission
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-root", type=Path, default=Path("/work"))
    parser.add_argument("--product", choices=("codex", "claude"), required=True)
    parser.add_argument(
        "--archive-root",
        type=Path,
        default=Path("/var/lib/tidmad-baseline/candidates"),
    )
    parser.add_argument(
        "--final-score",
        type=Path,
        default=Path("/var/lib/tidmad-baseline/final_score.json"),
    )
    args = parser.parse_args()
    print(finalize(args.work_root, args.product, args.archive_root, args.final_score))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
