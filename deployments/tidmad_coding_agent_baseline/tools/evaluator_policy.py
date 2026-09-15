"""Fail-closed path policy for the privileged task evaluator."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .model import BANDS

_SCOPE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class EvaluatorPolicy:
    """Evaluator-owned roots; none are selected by the agent."""

    input_root: Path = Path("/work/input")
    scope_root: Path = Path("/opt/tidmad-evaluator/assets/evaluation_scopes")
    raw_data_dir: Path = Path("/data/private-validation")
    agent_root: Path = Path("/work/agent")
    archive_root: Path = Path("/var/lib/tidmad-baseline/candidates")
    evaluation_root: Path = Path("/var/lib/tidmad-baseline/evaluations")
    health_config_root: Path = Path("/var/lib/tidmad-baseline/health-configs")
    final_score: Path = Path("/var/lib/tidmad-baseline/final_score.json")

    def agent_path(self, supplied: Path, *, label: str) -> Path:
        """Resolve an agent artifact and reject paths outside its workspace."""

        return _contained(self.agent_root, supplied, label=label)

    def scope_path(self, scope_name: str, *, band: str | None) -> Path:
        """Resolve a root-owned named evaluation scope."""

        if not _SCOPE_NAME.fullmatch(scope_name):
            raise ValueError(f"invalid evaluation scope name: {scope_name!r}")
        expected = "all" if band is None else band
        if expected not in (*BANDS, "all"):
            raise ValueError(f"unsupported evaluation scope band: {expected}")
        path = self.scope_root / f"{scope_name}.json"
        if not path.is_file():
            raise ValueError(f"frozen evaluation scope is missing: {scope_name}")
        payload = json.loads(path.read_text())
        observed = {int(value) for value in payload}
        if expected == "all":
            required = set(range(20))
        else:
            low, high = (int(value) for value in expected.split("-"))
            required = set(range(low, high + 1))
        if observed != required:
            raise ValueError(
                f"scope {scope_name!r} covers {sorted(observed)}, expected {sorted(required)}"
            )
        return path


def _contained(root: Path, supplied: Path, *, label: str) -> Path:
    resolved_root = root.resolve(strict=True)
    resolved = supplied.resolve(strict=True)
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"{label} must remain below {resolved_root}: {resolved}")
    return resolved
