"""Back up one NoPrior unit and stop its chain before its work disk fills.

The source is the external unit directory, never the frozen data directory.
S3 sync is append-only from the caller's perspective: it does not use --delete,
and the bucket must have versioning enabled. Large, retired intermediate
training/data files are excluded; certified .pt files and their provenance
are included.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from experiments.tidmad.main_fixed_workflow.unit_clock import read_launch_record

MIN_FREE_GIB = 50
_BUCKET = re.compile(r"[a-z0-9][a-z0-9.-]{2,62}")
# Fresh units may append a version; preserve the complete systemd identity.
_INSTANCE = re.compile(r"f-noprior-[0-9]+-[0-9]+(?:-[a-z0-9]+)*")
_EXCLUDES = (
    "*.pth",
    "*.h5",
    "*.hdf5",
    "*.h5.complete",
    "*.hdf5.complete",
    "*.tmp",
    "*.env",
    "*.log",
    "logs/*",
    ".supervisor.lock",
)


def _append_receipt(path: Path, payload: dict[str, object]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        os.write(descriptor, (json.dumps(payload, sort_keys=True) + "\n").encode())
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validated_unit(unit_dir: Path) -> tuple[Path, int]:
    source = unit_dir.absolute()
    if source.is_symlink() or not source.is_dir() or not source.parent.is_mount():
        raise ValueError("unit directory must be a real child of the mounted work volume")
    launch = read_launch_record(source / "launch.json")
    if launch is None:
        raise ValueError("unit has no immutable launch receipt")
    if launch.preflight.get("workspace") != str(source / "workspace"):
        raise ValueError("unit workspace disagrees with launch receipt")
    return source, launch.deadline_epoch


def check_space(*, unit_dir: Path, instance: str, min_free_gib: int = MIN_FREE_GIB) -> int:
    """Stop only this run if the mounted work volume is below its reserve."""

    if not _INSTANCE.fullmatch(instance):
        raise ValueError("invalid NoPrior service instance")
    if min_free_gib < 1:
        raise ValueError("minimum free space must be positive")
    source, _ = _validated_unit(unit_dir)
    free_bytes = shutil.disk_usage(source).free
    if free_bytes >= min_free_gib * 1024**3:
        return free_bytes
    stop = subprocess.run(
        ["systemctl", "stop", f"tidmad-no-prior@{instance}.service"],
        check=False,
        capture_output=True,
        text=True,
    )
    _append_receipt(
        source / "backup_receipts.jsonl",
        {
            "event": "low_space_stop",
            "epoch": int(time.time()),
            "free_bytes": free_bytes,
            "threshold_gib": min_free_gib,
            "stop_returncode": stop.returncode,
        },
    )
    if stop.returncode != 0:
        raise RuntimeError("failed to stop NoPrior service at low-space threshold")
    return free_bytes


def backup_unit(
    *,
    unit_dir: Path,
    bucket: str,
    prefix: str,
    endpoint: str,
    instance: str,
    min_free_gib: int = MIN_FREE_GIB,
) -> dict[str, object]:
    """Sync retained artifacts and leave a local receipt; never reset the clock."""

    if not _BUCKET.fullmatch(bucket):
        raise ValueError("invalid bucket")
    if not prefix or prefix.startswith("/") or ".." in Path(prefix).parts:
        raise ValueError("backup prefix must be a relative S3 key prefix")
    if not endpoint.startswith("https://"):
        raise ValueError("backup endpoint must use HTTPS")
    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        raise ValueError("backup S3 credentials are absent")

    source, deadline_epoch = _validated_unit(unit_dir)
    check_space(unit_dir=source, instance=instance, min_free_gib=min_free_gib)

    target = f"s3://{bucket}/{prefix.strip('/')}/"
    command = [
        "aws",
        "--endpoint-url",
        endpoint,
        "s3",
        "sync",
        str(source),
        target,
        "--no-follow-symlinks",
        "--only-show-errors",
    ]
    for pattern in _EXCLUDES:
        command += ["--exclude", pattern]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    receipt: dict[str, object] = {
        "event": "backup_sync",
        "epoch": int(time.time()),
        "launch_deadline_epoch": deadline_epoch,
        "bucket": bucket,
        "prefix": prefix.strip("/"),
        "free_bytes": shutil.disk_usage(source).free,
        "certified_checkpoint_count": sum(
            1 for path in (source / "workspace").rglob("*.pt") if path.is_file()
        ),
        "returncode": result.returncode,
    }
    _append_receipt(source / "backup_receipts.jsonl", receipt)
    if result.returncode != 0:
        raise RuntimeError(f"NoPrior artifact sync failed with exit code {result.returncode}")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-dir", type=Path, required=True)
    parser.add_argument("--bucket")
    parser.add_argument("--prefix")
    parser.add_argument("--endpoint")
    parser.add_argument("--instance", required=True)
    parser.add_argument("--min-free-gib", type=int, default=MIN_FREE_GIB)
    parser.add_argument("--check-space-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.check_space_only:
            check_space(
                unit_dir=args.unit_dir,
                instance=args.instance,
                min_free_gib=args.min_free_gib,
            )
        else:
            if not args.bucket or not args.prefix or not args.endpoint:
                parser.error("backup requires --bucket, --prefix and --endpoint")
            backup_unit(
                unit_dir=args.unit_dir,
                bucket=args.bucket,
                prefix=args.prefix,
                endpoint=args.endpoint,
                instance=args.instance,
                min_free_gib=args.min_free_gib,
            )
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"NoPrior backup refused: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
