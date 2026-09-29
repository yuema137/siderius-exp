"""Stamp a launcher policy's deadline just before it is installed.

`deadline_epoch` is an absolute time, so a policy drafted an hour before it
is installed has already spent an hour of its window. This restamps it from
now and verifies the result, so the gap between writing and installing is
whatever the two commands take rather than however long the operator was
away.

**What this deadline bounds.** One native invocation — `authorize_native_caller`
refuses when it has already passed, and the handler carries it into capture,
admission and training. It is NOT the campaign clock. The fixed workflow's
six hours are enforced by `main_fixed_workflow/unit_clock.py` and its
supervisor; the orchestration condition has no equivalent yet, so a caller
can still spend time thinking between native calls. Setting this to the
campaign's end means no training call outlives the campaign, which is worth
having and is not the same guarantee.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from experiments.phyts_tess.main_orchestrator.verify_launcher_policy import (
    verify_launcher_policy,
)

__all__ = ["stage_policy"]


def stage_policy(draft: Path, destination: Path, *, hours: float) -> dict:
    """Rewrite the draft with a fresh deadline, verify it, and return its receipt."""
    if hours <= 0:
        raise ValueError(f"deadline must be positive; got {hours}")
    payload = json.loads(Path(draft).read_text(encoding="utf-8"))
    deadline = time.time() + hours * 3600.0
    payload["deadline_epoch"] = deadline
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    receipt = verify_launcher_policy(destination)
    receipt["deadline_epoch"] = deadline
    receipt["deadline_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(deadline))
    receipt["hours"] = hours
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--hours",
        type=float,
        default=6.0,
        help="Wall-clock window for one native invocation. Default 6, matching "
        "the fixed workflow's unit budget.",
    )
    args = parser.parse_args(argv)

    receipt = stage_policy(args.draft, args.out, hours=args.hours)
    print(json.dumps(receipt, indent=2))
    print()
    # Owned by the coordinator, not root: the launcher reads it as that
    # account and refuses any other owner (DEPLOYMENT.md §4).
    print("install it, then probe:")
    print(
        f"  sudo install -o tess-coordinator -g root -m 0644 {args.out} "
        "/etc/tess-native/policy.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
