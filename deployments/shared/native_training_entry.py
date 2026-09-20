"""Isolated-Python bootstrap for an operator-installed native training wrapper.

Install under an immutable experiment checkout. A root-owned executable wrapper
fixes this script, the exact checkout interpreter and the policy argument before
appending the original native command. This script is not itself a sudoers rule.
"""

import sys
from pathlib import Path


def main() -> int:
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError("native launcher requires Python -I -B")
    if len(sys.argv) < 3:
        raise ValueError("native launcher requires fixed policy and native command")
    # -I removes the research cwd/PYTHONPATH. Only this script's installed checkout
    # is added; the operator owns its code and interpreter before granting sudo.
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from experiments.shared.native_launcher import dispatch_native_training

    return dispatch_native_training(Path(sys.argv[1]), sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
