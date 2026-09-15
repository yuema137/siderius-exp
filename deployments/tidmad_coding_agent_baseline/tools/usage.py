"""Extract non-overlapping final usage records from structured CLI traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _numbers(payload: dict[str, Any], names: tuple[str, ...]) -> dict[str, int]:
    return {
        name: int(payload.get(name, 0))
        for name in names
        if isinstance(payload.get(name, 0), (int, float))
    }


def usage_from_log(path: Path, product: str) -> dict[str, int]:
    """Return the final usage event from one invocation, never cumulative events."""

    selected: dict[str, int] = {}
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if product == "codex" and event.get("type") == "turn.completed":
            usage = event.get("usage", {})
            if isinstance(usage, dict):
                selected = _numbers(
                    usage, ("input_tokens", "cached_input_tokens", "output_tokens")
                )
        if product == "claude" and event.get("type") == "result":
            usage = event.get("usage", {})
            if isinstance(usage, dict):
                selected = _numbers(
                    usage,
                    (
                        "input_tokens",
                        "cache_creation_input_tokens",
                        "cache_read_input_tokens",
                        "output_tokens",
                    ),
                )
    return selected


def aggregate_usage(log_root: Path, product: str) -> dict[str, Any]:
    totals: dict[str, int] = {}
    missing: list[str] = []
    logs = sorted(log_root.glob(f"{product}-invocation-*.jsonl"))
    for path in logs:
        usage = usage_from_log(path, product)
        if not usage:
            missing.append(path.name)
        for name, value in usage.items():
            totals[name] = totals.get(name, 0) + value
    return {
        "product": product,
        "invocation_logs": len(logs),
        "totals": totals,
        "logs_without_final_usage": missing,
    }
