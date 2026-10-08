"""Generate and check literal saved-experiment shell entrypoints."""

from __future__ import annotations

import shlex
from pathlib import Path

from tutorials.shared.bootstrap import shell_setup_guard


def write_launcher(
    destination: Path, experiment: Path, *, checkout: Path, runner_module: str
) -> None:
    source = (
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        "# Edit the saved experiment; export credentials before running this script.\n"
        f"EXP_CHECKOUT={shlex.quote(str(checkout))}\n"
        f"EXPERIMENT={shlex.quote(str(experiment.resolve()))}\n"
        + shell_setup_guard()
        + 'cd "$EXP_CHECKOUT"\n'
        f'exec "$EXP_CHECKOUT/.venv/bin/python" -B -m {runner_module} '
        '--experiment "$EXPERIMENT" "$@"\n'
    )
    with destination.open("x") as stream:
        stream.write(source)
    destination.chmod(0o755)


def validate_launcher(
    experiment: Path, script: Path, *, checkout: Path, runner_module: str
) -> None:
    """Check the literal saved-file handoff before review or delegation.

    This checks generated-script bindings, not arbitrary shell-code safety.
    """
    lines = script.read_text().splitlines()
    for key, expected in (
        ("EXPERIMENT", experiment.resolve()),
        ("EXP_CHECKOUT", checkout),
    ):
        assignments = [
            line.split("=", 1)[1] for line in lines if line.startswith(key + "=")
        ]
        if len(assignments) != 1:
            raise ValueError(f"launcher must have one literal {key} binding")
        values = shlex.split(assignments[0])
        if (
            len(values) != 1
            or not Path(values[0]).is_absolute()
            or Path(values[0]).resolve() != expected
        ):
            raise ValueError(
                f"launcher {key} does not match the selected saved experiment/checkout"
            )
    entry = (
        f'exec "$EXP_CHECKOUT/.venv/bin/python" -B -m {runner_module} '
        '--experiment "$EXPERIMENT" "$@"'
    )
    if entry not in lines:
        raise ValueError("launcher is not the selected tutorial runner")
