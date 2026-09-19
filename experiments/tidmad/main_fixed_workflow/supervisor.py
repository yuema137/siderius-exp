"""Run one NoPrior chain under its write-once 24-hour UTC deadline."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from workflows.llm_config import WorkflowLLMConfig

from experiments.tidmad.main_fixed_workflow.band_inputs import BANDS
from experiments.tidmad.main_fixed_workflow.preflight import resolve_no_prior_launch
from experiments.tidmad.main_fixed_workflow.unit_clock import (
    LaunchRecord,
    create_launch_record,
    read_launch_record,
)


def _required_api_keys(config: Path) -> set[str]:
    """Read enabled provider names without displaying credentials."""

    provider_keys = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    payload = WorkflowLLMConfig.from_json(str(config)).model_dump(exclude_none=True)
    payload.pop("data_analysis", None)  # NoPrior disables this role explicitly.
    providers: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            provider = value.get("provider")
            if isinstance(provider, str):
                providers.add(provider)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    if not providers:
        raise ValueError("NoPrior LLM config declares no enabled provider")
    unknown = providers - provider_keys.keys()
    if unknown:
        raise ValueError(
            f"unsupported LLM provider in launch config: {sorted(unknown)}"
        )
    return {provider_keys[provider] for provider in providers}


def _verify_execution_environment(root: Path) -> None:
    """Require one H100 and name-only API key presence before starting a clock."""

    config = root / "experiments/tidmad/main_fixed_workflow/iclr_official_v1.json"
    missing = sorted(
        key for key in _required_api_keys(config) if not os.environ.get(key)
    )
    if missing:
        raise ValueError(f"required provider keys are absent: {', '.join(missing)}")
    gpu = subprocess.run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        check=True,
        capture_output=True,
        text=True,
    )
    names = [line.strip() for line in gpu.stdout.splitlines() if line.strip()]
    if len(names) != 1 or "H100" not in names[0]:
        raise ValueError(f"NoPrior unit requires exactly one H100; observed {names}")


def _append_event(path: Path, event: dict[str, object]) -> None:
    data = (json.dumps(event, sort_keys=True) + "\n").encode()
    descriptor = os.open(
        path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600
    )
    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _run_chain(record: LaunchRecord, unit_dir: Path) -> int:
    """Start or resume the same chain; kill its process group at the deadline."""

    remaining = record.deadline_epoch - time.time()
    if remaining <= 0:
        _append_event(unit_dir / "events.jsonl", {"event": "deadline_already_elapsed"})
        return 0
    # A permanent framework halt must survive service/operator restarts. Never
    # erase the marker or reset the immutable clock to retry an invalid chain.
    if (unit_dir / "workspace/.chain_halted").exists():
        _append_event(unit_dir / "events.jsonl", {"event": "chain_halt_preserved"})
        return 3
    command = record.preflight["command"]
    if not isinstance(command, list) or not all(
        isinstance(arg, str) for arg in command
    ):
        raise ValueError("stored NoPrior command is malformed")
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["SIDERIUS_GENERATED_LIBRARY_DIR"] = str(
        unit_dir / "workspace/generated_library"
    )
    # Fresh units cannot inherit host-wide timing evidence; resume reuses this path.
    environment["SIDERIUS_CALIBRATION_DIR"] = str(unit_dir / "calibration")
    logs = unit_dir / "logs"
    if logs.is_symlink():
        raise ValueError("NoPrior log directory must not be a symlink")
    logs.mkdir(mode=0o700, exist_ok=True)
    _append_event(
        unit_dir / "events.jsonl",
        {
            "event": "chain_start",
            "started_epoch": int(time.time()),
            "deadline_epoch": record.deadline_epoch,
        },
    )
    log_descriptor = os.open(
        logs / "chain.log",
        os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(log_descriptor, "ab", buffering=0) as output:
        process = subprocess.Popen(
            command,
            stdout=output,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=environment,
        )
        try:
            returncode = process.wait(
                timeout=max(0, record.deadline_epoch - time.time())
            )
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            _append_event(
                unit_dir / "events.jsonl",
                {"event": "deadline_stop", "ended_epoch": int(time.time())},
            )
            return 0
    _append_event(
        unit_dir / "events.jsonl",
        {
            "event": "chain_exit",
            "ended_epoch": int(time.time()),
            "returncode": returncode,
        },
    )
    if returncode == 3 or (unit_dir / "workspace/.chain_halted").exists():
        return 3
    return 0 if returncode == 0 else 1


def run_unit(
    *,
    root: Path,
    checkout: Path,
    band: str,
    data_dir: Path,
    unit_dir: Path,
    run_name: str,
    launch: bool,
) -> int:
    """Preview or supervise one external unit, preserving its first clock."""

    unit_dir = unit_dir.resolve()
    root = root.resolve()
    checkout = checkout.resolve()
    data_dir = data_dir.resolve()
    if any(
        unit_dir.is_relative_to(source) or source.is_relative_to(unit_dir)
        for source in (root, checkout, data_dir)
    ):
        raise ValueError("unit directory must be separate from checkouts and data")
    if launch and not unit_dir.parent.is_mount():
        raise ValueError(
            "NoPrior unit must be an immediate child of a mounted persistent volume"
        )
    record_path = unit_dir / "launch.json"
    if not launch:
        existing = read_launch_record(record_path)
        receipt = resolve_no_prior_launch(
            root,
            checkout,
            band=band,
            data_dir=data_dir,
            workspace=unit_dir / "workspace",
            run_name=run_name,
            require_fresh_workspace=existing is None,
        )
        if existing is not None and existing.preflight != receipt:
            raise ValueError("current NoPrior inputs differ from the recorded launch")
        print(
            json.dumps(
                {
                    "preflight": receipt,
                    "launch": existing.model_dump() if existing else None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    unit_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if unit_dir.stat().st_mode & 0o077:
        raise ValueError(
            "NoPrior unit directory must be private to the service account"
        )
    lock_descriptor = os.open(
        unit_dir / ".supervisor.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(lock_descriptor, "a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        existing = read_launch_record(record_path)
        if existing is None and set(unit_dir.iterdir()) != {
            unit_dir / ".supervisor.lock"
        }:
            raise ValueError("new NoPrior unit directory must be empty")
        receipt = resolve_no_prior_launch(
            root,
            checkout,
            band=band,
            data_dir=data_dir,
            workspace=unit_dir / "workspace",
            run_name=run_name,
            require_fresh_workspace=existing is None,
        )
        if existing is not None and existing.preflight != receipt:
            raise ValueError("current NoPrior inputs differ from the recorded launch")
        if existing is not None and existing.deadline_epoch <= time.time():
            return 0
        _verify_execution_environment(root)
        record = existing or create_launch_record(
            record_path, receipt, int(time.time())
        )
        return _run_chain(record, unit_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--siderius-checkout", type=Path, required=True)
    parser.add_argument("--band", choices=tuple(BANDS), required=True)
    parser.add_argument("--data_dir", type=Path, required=True)
    parser.add_argument("--unit-dir", type=Path, required=True)
    parser.add_argument("--run_name", required=True)
    parser.add_argument(
        "--launch", action="store_true", help="start or resume the 24-hour unit"
    )
    args = parser.parse_args()
    try:
        return run_unit(
            root=Path(__file__).resolve().parents[3],
            checkout=args.siderius_checkout,
            band=args.band,
            data_dir=args.data_dir,
            unit_dir=args.unit_dir,
            run_name=args.run_name,
            launch=args.launch,
        )
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"NoPrior launch refused: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
