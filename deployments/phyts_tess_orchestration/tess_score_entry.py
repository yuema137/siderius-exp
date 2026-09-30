"""Isolated-Python bootstrap for the operator-installed `tess-score` wrapper.

Install under an immutable experiment checkout. A root-owned executable wrapper
fixes this script, the exact checkout interpreter and the evaluator policy
argument before appending the caller's scoring arguments. This script is not
itself a sudoers rule.

Mirrors `deployments/shared/native_training_entry.py`.
"""

import sys
from pathlib import Path


def main() -> int:
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError("tess-score requires Python -I -B")
    if len(sys.argv) < 3:
        raise ValueError(
            "tess-score requires the fixed policy path and scoring arguments"
        )
    # -I removes the caller's cwd/PYTHONPATH. Only this script's installed
    # checkout is added; the operator owns its code and interpreter before
    # granting sudo. The scorer then puts the frozen evaluator view in front.
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from experiments.phyts_tess.main_orchestrator.tess_score import main as score

    return score(Path(sys.argv[1]), sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
