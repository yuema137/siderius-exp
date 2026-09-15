"""Construct explicit, product-specific CLI invocations."""

from __future__ import annotations

from pathlib import Path

from .model import AgentProduct


def command_for(product: AgentProduct, prompt: Path) -> list[str]:
    if product == "codex":
        return [
            "codex",
            "-a",
            "never",
            "-s",
            "danger-full-access",
            "--search",
            "exec",
            "-m",
            "gpt-5.6-sol",
            "-c",
            'model_reasoning_effort="medium"',
            "--json",
            "-",
        ]
    if product == "claude":
        return [
            "claude",
            "-p",
            "--model",
            "opus",
            "--effort",
            "medium",
            "--dangerously-skip-permissions",
            "--permission-prompts",
            "none",
            "--output-format",
            "stream-json",
            "--verbose",
        ]
    raise ValueError(f"unsupported agent product: {product!r}")


def prompt_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if not data.strip():
        raise ValueError(f"agent prompt is empty: {path}")
    return data
