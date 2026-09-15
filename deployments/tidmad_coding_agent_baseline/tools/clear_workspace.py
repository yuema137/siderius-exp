"""Remove drill state without touching immutable inputs, harness or data."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from .io import sha256_file

RESET_CHILDREN = ("agent", "state", "submission", "logs")
PRESERVED_CHILDREN = ("input", "harness")
ACTIVE_UNITS = (
    "tidmad-coding-agent.service",
    "tidmad-baseline-start.timer",
    "tidmad-baseline-stop.timer",
)


def _verify_manifest(input_root: Path) -> None:
    manifest = input_root / "bundle.sha256"
    if not manifest.is_file():
        raise ValueError(f"frozen input manifest missing: {manifest}")
    for line_number, raw_line in enumerate(manifest.read_text().splitlines(), start=1):
        if not raw_line.strip():
            continue
        expected, relative = raw_line.split(maxsplit=1)
        relative = relative.lstrip("*")
        target = input_root / relative
        if not target.is_file() or sha256_file(target) != expected:
            raise ValueError(
                f"input manifest mismatch at line {line_number}: {relative}"
            )


def clear_workspace(
    work_root: Path, owner: str | None = None, group: str | None = None
) -> None:
    root = work_root.resolve()
    if not root.is_absolute() or root == Path("/") or len(root.parts) < 3:
        raise ValueError(f"unsafe work root: {root}")
    for child in PRESERVED_CHILDREN:
        if not (root / child).is_dir():
            raise ValueError(f"required preserved directory missing: {root / child}")
    _verify_manifest(root / "input")
    for child in RESET_CHILDREN:
        target = root / child
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, mode=0o770)
        target.chmod(0o2770)
        if owner is not None or group is not None:
            shutil.chown(target, user=owner, group=group)
    _verify_manifest(root / "input")


def clear_retained_state(
    retained_root: Path,
    evaluator_user: str,
    results_group: str,
    backup_user: str,
    *,
    expected_root: Path = Path("/var/lib/tidmad-baseline"),
) -> None:
    root = retained_root.resolve()
    if root != expected_root.resolve():
        raise ValueError(f"unexpected retained-state root: {root}")
    for name in (
        "candidates",
        "evaluations",
        "health-configs",
        "backup-receipts",
    ):
        target = root / name
        if target.exists():
            shutil.rmtree(target)
    for name in ("final_score.json",):
        (root / name).unlink(missing_ok=True)
    candidates = root / "candidates"
    candidates.mkdir(mode=0o2750)
    candidates.chmod(0o2750)
    shutil.chown(candidates, user=evaluator_user, group=results_group)
    for name in ("evaluations", "health-configs"):
        target = root / name
        target.mkdir(mode=0o2750)
        target.chmod(0o2750)
        shutil.chown(target, user=evaluator_user, group=results_group)
    receipts = root / "backup-receipts"
    receipts.mkdir(mode=0o700)
    shutil.chown(receipts, user=backup_user, group=backup_user)


def _require_services_stopped() -> None:
    active = [
        unit
        for unit in ACTIVE_UNITS
        if subprocess.run(
            ["systemctl", "is-active", "--quiet", unit], check=False
        ).returncode
        == 0
    ]
    if active:
        raise RuntimeError(f"refuse to clear while baseline units are active: {active}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-root", type=Path, default=Path("/work"))
    parser.add_argument("--owner")
    parser.add_argument("--group")
    parser.add_argument(
        "--retained-root", type=Path, default=Path("/var/lib/tidmad-baseline")
    )
    args = parser.parse_args()
    if (args.owner is not None or args.group is not None) and os.geteuid() != 0:
        parser.error("--owner/--group require root")
    _require_services_stopped()
    clear_workspace(args.work_root, owner=args.owner, group=args.group)
    clear_retained_state(
        args.retained_root,
        evaluator_user="baseline-evaluator",
        results_group="baseline-results",
        backup_user="baseline-backup",
    )
    print("workspace reset; frozen input manifest verified before and after")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
