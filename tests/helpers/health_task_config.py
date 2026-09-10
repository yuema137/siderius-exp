"""Write a minimal persisted Health roster for campaign eligibility tests."""

from pathlib import Path

import yaml

from execute_tools.health_checks.config import EFFECTIVE_CONFIG_BASENAME


def write_pinned_effective_config(workspace: str | Path, gate_ids: list[str]) -> str:
    """Write the exact persisted shape read by workspace eligibility checks."""
    root = Path(workspace)
    root.mkdir(parents=True, exist_ok=True)
    document = {
        "health_gates": [
            {
                "id": gate_id,
                "gate_role": "blocking",
                "after_round": "every",
                "short_circuit": True,
                "checks": [{"name": "output_std", "config": {}}],
                "on_pass": {"action": "continue"},
                "on_fail": {"action": "invalidate_round"},
                "reason": "test roster declared but not evaluated",
            }
            for gate_id in gate_ids
        ],
        "task_health_binding": "explicit",
    }
    path = root / EFFECTIVE_CONFIG_BASENAME
    path.write_text(yaml.safe_dump(document, sort_keys=True), encoding="utf-8")
    return str(path)
