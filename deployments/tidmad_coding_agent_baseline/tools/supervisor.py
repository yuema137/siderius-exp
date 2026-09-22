"""Run repeated CLI invocations against one immutable experiment clock."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from .agent_command import command_for, prompt_bytes
from .deadline import load_or_create
from .io import create_json_once
from .model import AgentProduct, utc_text
from .prompt_supplement import append_verified_supplement


def _append_receipt(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(payload, sort_keys=True) + "\n").encode()
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, line)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _wait_for_start(start_epoch: int) -> None:
    while True:
        remaining = start_epoch - time.time()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 30))


def _run_once(
    *,
    product: AgentProduct,
    prompt: Path,
    log_path: Path,
    deadline_epoch: int,
    run_id: str,
    invocation_id: str,
    prompt_supplement: Path | None = None,
) -> tuple[int, bool]:
    command = command_for(product, prompt)
    prompt_input = append_verified_supplement(prompt_bytes(prompt), prompt_supplement)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab", buffering=0) as output:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={
                **os.environ,
                "BASELINE_RUN_ID": run_id,
                "BASELINE_INVOCATION_ID": invocation_id,
            },
        )
        assert process.stdin is not None
        process.stdin.write(prompt_input)
        process.stdin.close()
        remaining = max(0, deadline_epoch - int(time.time()))
        try:
            return process.wait(timeout=remaining), False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGINT)
            try:
                return process.wait(timeout=120), True
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return process.wait(), True


def supervise(
    *,
    product: AgentProduct,
    work_root: Path,
    prompt: Path,
    scheduled_start_epoch: int,
    prompt_supplement: Path | None = None,
) -> None:
    # Refuse a broken deployment before creating its scientific clock.
    if prompt_supplement is not None:
        append_verified_supplement(prompt_bytes(prompt), prompt_supplement)
    state = work_root / "state"
    logs = work_root / "logs"
    deadline = load_or_create(state / "deadline.json", scheduled_start_epoch)
    _wait_for_start(deadline.scheduled_start_epoch)
    actual_start = int(time.time())
    run_id = f"{product}-{deadline.scheduled_start_epoch}"
    create_json_once(
        state / "run_start.json",
        {
            "version": "tidmad-coding-agent-run-start-v1",
            "product": product,
            "run_id": run_id,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "scheduled_start_epoch": deadline.scheduled_start_epoch,
            "scheduled_start_utc": utc_text(deadline.scheduled_start_epoch),
            "actual_start_epoch": actual_start,
            "actual_start_utc": utc_text(actual_start),
        },
    )

    receipts = state / "invocations.jsonl"
    invocation = sum(1 for _ in receipts.open("rb")) if receipts.exists() else 0
    while int(time.time()) < deadline.agent_deadline_epoch:
        invocation += 1
        invocation_id = f"{run_id}-invocation-{invocation:04d}"
        started = int(time.time())
        log_path = logs / f"{product}-invocation-{invocation:04d}.jsonl"
        returncode, deadline_stop = _run_once(
            product=product,
            prompt=prompt,
            log_path=log_path,
            deadline_epoch=deadline.agent_deadline_epoch,
            run_id=run_id,
            invocation_id=invocation_id,
            prompt_supplement=prompt_supplement,
        )
        ended = int(time.time())
        _append_receipt(
            receipts,
            {
                "invocation": invocation,
                "invocation_id": invocation_id,
                "started_epoch": started,
                "started_utc": utc_text(started),
                "ended_epoch": ended,
                "ended_utc": utc_text(ended),
                "returncode": returncode,
                "stopped_at_agent_deadline": deadline_stop,
                "log": str(log_path),
            },
        )
        if ended < deadline.agent_deadline_epoch:
            time.sleep(min(30, deadline.agent_deadline_epoch - ended))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", choices=("codex", "claude"), required=True)
    parser.add_argument("--work-root", type=Path, default=Path("/work"))
    parser.add_argument("--prompt", type=Path, default=Path("/work/input/task.md"))
    parser.add_argument("--scheduled-start-epoch", type=int, required=True)
    parser.add_argument("--prompt-supplement", type=Path)
    args = parser.parse_args()
    supervise(
        product=args.product,
        work_root=args.work_root,
        prompt=args.prompt,
        scheduled_start_epoch=args.scheduled_start_epoch,
        prompt_supplement=args.prompt_supplement,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
