"""Exercise the real CLI permission, network, GPU and checkpoint path."""

from __future__ import annotations

import argparse
import re
import subprocess
import time
from pathlib import Path

from .agent_command import command_for
from .io import atomic_write_json, sha256_file
from .model import utc_text

SMOKE_PROMPT = """This is a pre-budget smoke test, not the scientific run.
Work only below {root}. Without asking for human approval:
1. create result/write-ok.txt;
2. run Python and record its version in result/python.txt;
3. run nvidia-smi and record its unedited output in result/gpu.txt;
4. fetch https://example.com and record the HTTP result in result/network.txt;
5. create a fresh venv, install the small package 'packaging', import it, and
   record its version in result/package.txt;
6. use PyTorch to save a tiny checkpoint as result/checkpoint.pt, reload it,
   confirm equality, and write result/reload-ok.txt;
7. write result/COMPLETE with a concise success report, including the model
   identity the product says is serving this invocation; then exit normally.
Do not inspect any scientific data or prior workspace.
"""

_REQUIRED_RESULTS = (
    "write-ok.txt",
    "python.txt",
    "gpu.txt",
    "network.txt",
    "package.txt",
    "checkpoint.pt",
    "reload-ok.txt",
    "COMPLETE",
)


def _verify_results(root: Path) -> dict[str, str]:
    result_root = root / "result"
    missing = [
        name
        for name in _REQUIRED_RESULTS
        if not (result_root / name).is_file()
        or (result_root / name).stat().st_size == 0
    ]
    if missing:
        raise RuntimeError(f"smoke result is missing non-empty artifacts: {missing}")
    gpu_text = (result_root / "gpu.txt").read_text(errors="replace")
    if "H100" not in gpu_text.upper():
        raise RuntimeError("smoke result does not prove an H100 was visible")
    reload_text = (result_root / "reload-ok.txt").read_text(errors="replace")
    if "ok" not in reload_text.lower():
        raise RuntimeError("smoke result does not confirm checkpoint reload")
    return {name: sha256_file(result_root / name) for name in _REQUIRED_RESULTS}


def _help_text(product: str) -> str:
    commands = [[product, "--help"]]
    if product == "codex":
        commands.append([product, "exec", "--help"])
    outputs = []
    for command in commands:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=30
        )
        outputs.append(result.stdout + result.stderr)
    return "\n".join(outputs)


def _required_flags(product: str) -> tuple[str, ...]:
    if product == "codex":
        return (
            "--ask-for-approval",
            "--sandbox",
            "--search",
            "--model",
            "--config",
            "--json",
        )
    return (
        "--dangerously-skip-permissions",
        "--permission-prompts",
        "--effort",
        "--model",
        "--output-format",
    )


def smoke(
    product: str, root: Path, expected_model_regex: str, timeout_seconds: int
) -> Path:
    root.mkdir(parents=True, exist_ok=False)
    started = int(time.time())
    version = subprocess.run(
        [product, "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    help_text = _help_text(product)
    missing = [flag for flag in _required_flags(product) if flag not in help_text]
    if missing:
        raise RuntimeError(f"{product} CLI is missing required flags: {missing}")
    prompt = root / "smoke-prompt.md"
    prompt.write_text(SMOKE_PROMPT.format(root=root))
    log = root / "cli.jsonl"
    with prompt.open("rb") as stdin, log.open("wb") as output:
        result = subprocess.run(
            command_for(product, prompt),
            stdin=stdin,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
            check=False,
        )
    if result.returncode != 0:
        raise RuntimeError(f"{product} smoke exited {result.returncode}; inspect {log}")
    result_hashes = _verify_results(root)
    if (
        re.search(expected_model_regex, log.read_text(errors="replace"), re.IGNORECASE)
        is None
    ):
        raise RuntimeError(
            f"served model identity matching {expected_model_regex!r} absent from {log}"
        )
    ended = int(time.time())
    atomic_write_json(
        root / "smoke_receipt.json",
        {
            "version": "tidmad-coding-agent-smoke-v1",
            "product": product,
            "cli_version": version,
            "expected_served_model_regex": expected_model_regex,
            "structured_log_sha256": sha256_file(log),
            "result_sha256": result_hashes,
            "started_epoch": started,
            "started_utc": utc_text(started),
            "ended_epoch": ended,
            "ended_utc": utc_text(ended),
            "completed_without_prompt": True,
        },
    )
    return log


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", choices=("codex", "claude"), required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-model-regex", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()
    print(
        smoke(args.product, args.root, args.expected_model_regex, args.timeout_seconds)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
