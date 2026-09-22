"""Explicit operator-reviewed continuation after a collected infrastructure failure.

This entry point neither clears a halt nor deletes failed artifacts. The operator
must collect and verify the original unit, qualify restoration, and prepare the
failed tail before launch. Ordinary supervisor restarts retain their old policy.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import time
from pathlib import Path

from experiments.shared.checksum_manifest import sha256_file
from experiments.tidmad.main_fixed_workflow.full_binding import FullAnalysisInputs
from experiments.tidmad.main_fixed_workflow.preflight import (
    resolve_full_launch,
    resolve_no_prior_launch,
)
from experiments.tidmad.main_fixed_workflow.supervisor import (
    _run_chain,
    _verify_execution_environment,
)
from experiments.tidmad.main_fixed_workflow.unit_clock import (
    UNIT_SECONDS,
    ContinuationRecord,
    publish_continuation,
    read_launch_record,
)


def verify_recovery_inputs(original: dict, current: dict) -> None:
    """Only source revisions may change; all paths and scientific inputs persist."""
    allowed = {"repository_revision", "siderius_revision"}
    before = {k: v for k, v in original.items() if k not in allowed}
    after = {k: v for k, v in current.items() if k not in allowed}
    if before != after:
        changed = sorted(
            k for k in before.keys() | after.keys() if before.get(k) != after.get(k)
        )
        raise ValueError(f"continuation changes frozen inputs: {changed}")


def run_continuation(
    *,
    root: Path,
    checkout: Path,
    unit: Path,
    stopped_epoch: int,
    evidence: Path,
    launch: bool,
) -> int:
    """Reuse one separately recorded remaining-time clock across service restarts."""
    unit = unit.resolve()
    if unit.stat().st_mode & 0o077 or not unit.parent.is_mount():
        raise ValueError("continuation requires a private unit on a persistent mount")
    descriptor = os.open(unit / ".supervisor.lock", os.O_RDWR | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original_path = unit / "launch.json"
        original = read_launch_record(original_path)
        if original is None:
            raise ValueError("original launch record is required")
        # Bind the downtime claim to an actual recorded failure, not a new allowance.
        events = [
            json.loads(line)
            for line in (unit / "events.jsonl").read_text().splitlines()
        ]
        if not any(
            e.get("event") == "chain_exit"
            and e.get("returncode") in (1, 3)
            and e.get("ended_epoch") == stopped_epoch
            for e in events
        ):
            raise ValueError("stopped_epoch must match a recorded failed chain exit")
        prior = original.preflight
        arguments = {
            "band": prior["data"]["band"],
            "data_dir": Path(prior["data_dir"]),
            "workspace": unit / "workspace",
            "run_name": prior["run_name"],
            "require_fresh_workspace": False,
        }
        binding = prior.get("analysis_binding")
        if binding:
            current = resolve_full_launch(
                root,
                checkout,
                **arguments,
                full_analysis=FullAnalysisInputs(
                    policy_path=Path(binding["analysis_policy_path"]),
                    policy_sha256=binding["analysis_policy_sha256"],
                    composition_path=Path(binding["composition_path"]),
                    model_advice=binding.get("model_advice", True),
                ),
            )
        else:
            current = resolve_no_prior_launch(root, checkout, **arguments)
        verify_recovery_inputs(prior, current)
        path = unit / "continuation.json"
        if path.is_symlink():
            raise ValueError("continuation record must not be a symlink")
        identity = {
            "original_launch_sha256": sha256_file(original_path),
            "original_started_epoch": original.started_epoch,
            "stopped_epoch": stopped_epoch,
            "recovery_evidence_sha256": sha256_file(evidence),
            "preflight": current,
        }
        existing = (
            ContinuationRecord.model_validate_json(path.read_bytes())
            if path.exists()
            else None
        )
        if existing and any(getattr(existing, k) != v for k, v in identity.items()):
            raise ValueError(
                "continuation inputs differ from the immutable recovery record"
            )
        if (unit / "workspace/.chain_halted").exists():
            raise ValueError(
                "halt remains: complete reviewed recovery preparation first"
            )
        if launch:
            _verify_execution_environment(root, include_analysis=bool(binding))
        now = int(time.time())
        record = existing or ContinuationRecord(
            version="tidmad-main-fixed-continuation-v1",
            **identity,
            started_epoch=now,
            deadline_epoch=now
            + UNIT_SECONDS
            - (stopped_epoch - original.started_epoch),
        )
        if not launch:
            print(record.model_dump_json(indent=2))
            return 0
        if existing is None:
            publish_continuation(path, record)
        return _run_chain(record, unit)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--siderius-checkout", type=Path, required=True)
    parser.add_argument("--unit-dir", type=Path, required=True)
    parser.add_argument("--stopped-epoch", type=int, required=True)
    parser.add_argument("--recovery-evidence", type=Path, required=True)
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args()
    try:
        return run_continuation(
            root=Path(__file__).resolve().parents[3],
            checkout=args.siderius_checkout.resolve(),
            unit=args.unit_dir,
            stopped_epoch=args.stopped_epoch,
            evidence=args.recovery_evidence,
            launch=args.launch,
        )
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Continuation refused: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
