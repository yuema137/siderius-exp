"""Publish completed candidates to S3 with create-only semantics."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

from .io import create_json_once, sha256_file
from .model import BANDS, utc_text


def _aws(*args: str, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    endpoint = os.environ.get("BACKUP_ENDPOINT")
    command = ["aws"]
    if endpoint:
        command.extend(("--endpoint-url", endpoint))
    return subprocess.run(
        [*command, *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )


def _publish_one(
    candidate: Path,
    *,
    bucket: str,
    prefix: str,
    receipts: Path,
    timeout_seconds: int,
) -> str:
    manifest = candidate / "candidate_manifest.json"
    if not manifest.is_file() or not (candidate / "COMPLETE.json").is_file():
        raise ValueError(f"candidate is not complete: {candidate}")
    digest = sha256_file(manifest)
    band = candidate.parent.name
    key = "/".join(
        part
        for part in (
            prefix.strip("/"),
            "candidates",
            band,
            f"{candidate.name}-{digest}.tar.gz",
        )
        if part
    )
    receipt = receipts / band / f"{candidate.name}.json"
    if receipt.exists():
        return "already-recorded"

    with tempfile.TemporaryDirectory(prefix="tidmad-baseline-backup-") as raw:
        archive = Path(raw) / "candidate.tar.gz"
        _archive_tree(candidate, archive)
        archive_digest = sha256_file(archive)
        result = _aws(
            "s3api",
            "put-object",
            "--bucket",
            bucket,
            "--key",
            key,
            "--body",
            str(archive),
            "--if-none-match",
            "*",
            "--metadata",
            f"sha256={archive_digest},candidate-manifest-sha256={digest}",
            "--cli-connect-timeout",
            "15",
            "--cli-read-timeout",
            str(min(timeout_seconds, 300)),
            timeout_seconds=timeout_seconds,
        )
        if result.returncode != 0:
            combined = f"{result.stdout}\n{result.stderr}"
            if "PreconditionFailed" not in combined and "412" not in combined:
                raise RuntimeError(
                    f"append-only candidate upload failed: {combined.strip()}"
                )
            existing = _aws(
                "s3api",
                "head-object",
                "--bucket",
                bucket,
                "--key",
                key,
                timeout_seconds=timeout_seconds,
            )
            if existing.returncode != 0:
                raise RuntimeError("existing backup object could not be verified")
            metadata = json.loads(existing.stdout).get("Metadata", {})
            if metadata.get("candidate-manifest-sha256") != digest:
                raise RuntimeError(
                    "existing backup object has different candidate identity"
                )
        create_json_once(
            receipt,
            {
                "version": "tidmad-coding-agent-backup-v1",
                "bucket": bucket,
                "key": key,
                "archive_sha256": archive_digest,
                "candidate_manifest_sha256": digest,
                "created": result.returncode == 0,
                "event_utc": utc_text(time.time()),
            },
        )
    return "created" if result.returncode == 0 else "already-existed"


def _archive_tree(source: Path, archive: Path) -> None:
    with (
        archive.open("wb") as raw_archive,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw_archive, mtime=0) as zipped,
        tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar,
    ):
        tar.add(source, arcname=source.name, recursive=True, filter=_tar_info)


def _publish_submission(
    submission: Path,
    *,
    bucket: str,
    prefix: str,
    receipts: Path,
    timeout_seconds: int,
) -> str | None:
    manifest = submission / "manifest.json"
    if not manifest.is_file() or not (submission / "COMPLETE.json").is_file():
        return None
    digest = sha256_file(manifest)
    receipt = receipts / "submission.json"
    if receipt.exists():
        return "already-recorded"
    key = "/".join(
        part
        for part in (
            prefix.strip("/"),
            "submission",
            f"submission-{digest}.tar.gz",
        )
        if part
    )
    with tempfile.TemporaryDirectory(prefix="tidmad-baseline-final-backup-") as raw:
        archive = Path(raw) / "submission.tar.gz"
        _archive_tree(submission, archive)
        archive_digest = sha256_file(archive)
        result = _aws(
            "s3api",
            "put-object",
            "--bucket",
            bucket,
            "--key",
            key,
            "--body",
            str(archive),
            "--if-none-match",
            "*",
            "--metadata",
            f"sha256={archive_digest},submission-manifest-sha256={digest}",
            "--cli-connect-timeout",
            "15",
            "--cli-read-timeout",
            str(min(timeout_seconds, 300)),
            timeout_seconds=timeout_seconds,
        )
        if result.returncode != 0:
            combined = f"{result.stdout}\n{result.stderr}"
            if "PreconditionFailed" not in combined and "412" not in combined:
                raise RuntimeError(
                    f"append-only submission upload failed: {combined.strip()}"
                )
        create_json_once(
            receipt,
            {
                "version": "tidmad-coding-agent-final-backup-v1",
                "bucket": bucket,
                "key": key,
                "archive_sha256": archive_digest,
                "submission_manifest_sha256": digest,
                "created": result.returncode == 0,
                "event_utc": utc_text(time.time()),
            },
        )
    return "created" if result.returncode == 0 else "already-existed"


def _tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = 0
    return info


def backup_completed(
    archive_root: Path,
    *,
    bucket: str,
    prefix: str,
    receipts: Path,
    timeout_seconds: int,
    submission_root: Path | None = None,
) -> list[tuple[Path, str]]:
    outcomes: list[tuple[Path, str]] = []
    for band in BANDS:
        band_root = archive_root / band
        if not band_root.is_dir():
            continue
        for candidate in sorted(band_root.iterdir()):
            if candidate.is_dir() and not candidate.name.startswith("."):
                outcomes.append(
                    (
                        candidate,
                        _publish_one(
                            candidate,
                            bucket=bucket,
                            prefix=prefix,
                            receipts=receipts,
                            timeout_seconds=timeout_seconds,
                        ),
                    )
                )
    if submission_root is not None:
        outcome = _publish_submission(
            submission_root,
            bucket=bucket,
            prefix=prefix,
            receipts=receipts,
            timeout_seconds=timeout_seconds,
        )
        if outcome is not None:
            outcomes.append((submission_root, outcome))
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive-root", type=Path, default=Path("/work/state/candidates")
    )
    parser.add_argument(
        "--receipt-root", type=Path, default=Path("/work/state/backup_receipts")
    )
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--submission-root", type=Path, default=Path("/work/submission"))
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    for path, outcome in backup_completed(
        args.archive_root,
        bucket=args.bucket,
        prefix=args.prefix,
        receipts=args.receipt_root,
        timeout_seconds=args.timeout_seconds,
        submission_root=args.submission_root,
    ):
        print(f"{outcome}\t{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
