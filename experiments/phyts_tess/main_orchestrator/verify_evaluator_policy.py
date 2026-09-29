"""Check an evaluator policy before the coordinator reads it under sudo.

The sibling of `verify_launcher_policy.py` for `tess-score`. A draft is
checked for content; `--installed` adds the ownership and parent-chain rules
`read_evaluator_policy` enforces, which only mean anything once the file is
at the path the wrapper fixes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.phyts_tess.main_orchestrator.tess_score import (
    _VIEW_HEALTH,
    _VIEW_MANIFEST,
    _VIEW_METRICS,
    _VIEW_PROFILE,
    TessEvaluatorPolicy,
)
from experiments.phyts_tess.main_orchestrator.verify_launcher_policy import (
    _verify_installed_ownership,
)

__all__ = ["verify_evaluator_policy"]

_VIEW_SCORER = Path("tasks/phyts_tess/runtime/scoring.py")
_VAL_ARCHIVE = "tess_rotation_val.npz"


def verify_evaluator_policy(
    path: Path, *, installed: bool = False
) -> dict[str, object]:
    """Validate a policy; raise on the first thing that is wrong."""
    policy = TessEvaluatorPolicy.model_validate_json(path.read_bytes())
    view = policy.evaluator_view
    for required in (
        _VIEW_MANIFEST,
        _VIEW_PROFILE,
        _VIEW_HEALTH,
        _VIEW_SCORER,
        *_VIEW_METRICS.values(),
    ):
        if not (view / required).is_file():
            raise ValueError(f"evaluator view lacks {required}: {view}")
    archive = policy.validation_data / _VAL_ARCHIVE
    if not archive.is_file():
        raise ValueError(
            f"validation data lacks {_VAL_ARCHIVE}: {policy.validation_data}"
        )
    profile = json.loads((view / _VIEW_PROFILE).read_text(encoding="utf-8"))
    declared = profile["topology"]["populations"]["val"]
    if installed:
        _verify_installed_ownership(path, policy.coordinator_uid)
    return {
        "policy": str(path),
        "caller_uid": policy.caller_uid,
        "coordinator_uid": policy.coordinator_uid,
        "evaluator_view": str(view),
        "declared_val_rows": declared,
        "installed_checks": installed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", type=Path)
    parser.add_argument(
        "--installed",
        action="store_true",
        help="also verify ownership and the parent chain at this exact path",
    )
    args = parser.parse_args(argv)
    print(
        json.dumps(
            verify_evaluator_policy(args.policy, installed=args.installed), indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
