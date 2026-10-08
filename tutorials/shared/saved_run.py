"""Saved-script cache, console log and subprocess supervision mechanics."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

import psutil


def run_saved_script(
    *,
    script: Path,
    workspace: Path,
    digest: str,
    ready: Callable[[], None],
    timeout_seconds: float,
) -> dict:
    """Reuse a matching completed run or call readiness then launch the saved script.

    Task adapters validate saved settings/bindings and supply the input digest.
    Readiness runs only for a fresh launch, before directories/logs are created.
    """
    completion = workspace.with_suffix(".notebook-run.json")
    log_path = workspace.with_suffix(".console.log")
    if completion.exists():
        result = json.loads(completion.read_text())
        if result["input_sha256"] != digest:
            raise ValueError(
                "Inputs changed after this run. Keep old results and select a fresh workspace/run name before executing."
            )
        if not workspace.is_dir():
            raise ValueError(
                "Completed workspace is missing; restore it or choose a new run"
            )
        if result["exit_code"] != 0:
            raise RuntimeError(
                f"Previous script run failed; inspect {log_path} before selecting a new workspace"
            )
        print(f"Reusing recorded result without API/GPU work: {workspace}")
        return result
    if workspace.exists() or log_path.exists():
        raise ValueError(
            f"Existing or interrupted run; inspect {log_path}. Nothing was relaunched."
        )
    ready()
    workspace.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with log_path.open("x") as log:
        process = subprocess.Popen(
            ["bash", str(script), "--launch"],
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        print(f"Running saved script: {script}\nLive log: {log_path}", flush=True)
        try:
            while True:
                remaining = timeout_seconds - (time.monotonic() - start)
                if remaining <= 0:
                    raise TimeoutError(
                        "Notebook time limit reached; stopped the entire run process group"
                    )
                try:
                    code = process.wait(timeout=min(30, remaining))
                    break
                except subprocess.TimeoutExpired:
                    print(
                        f"Running: {(time.monotonic() - start) / 60:.1f} min; inspect {log_path.name}",
                        flush=True,
                    )
        except BaseException:
            # Measurement workers may start their own session; killpg alone
            # cannot reach them. Capture descendants before terminating parents.
            try:
                descendants = psutil.Process(process.pid).children(recursive=True)
            except psutil.NoSuchProcess:
                descendants = []
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            for child in descendants:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            _, alive = psutil.wait_procs(descendants, timeout=5)
            for child in alive:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
    result = {
        "input_sha256": digest,
        "exit_code": code,
        "elapsed_seconds": time.monotonic() - start,
        "workspace": str(workspace),
        "log": str(log_path),
    }
    with completion.open("x") as stream:
        json.dump(result, stream, indent=2)
    if code:
        raise RuntimeError(
            f"Saved script exited {code}. Inspect {log_path}; do not silently rerun an incomplete workspace."
        )
    return result
