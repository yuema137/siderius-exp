"""Supervise one prepared fixed-workflow campaign as a non-root child.

Run the supervisor as the deployment operator. It owns the credential file,
immutable clock and logs; generated code runs under the declared worker UID.
Default mode is a preflight preview. Only --launch starts or resumes a clock.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import stat
import subprocess
import time
from pathlib import Path

from experiments.shared.fixed_unit_clock import create_clock, read_clock
from experiments.shared.prepared_unit_preflight import (
    PreparedPreflight,
    resolve_preflight,
)


def read_credentials(path: Path, required: tuple[str, ...]) -> dict[str, str]:
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != 0
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise PermissionError(
            "credential file must be root-owned, regular, and mode 0600"
        )
    try:
        values = json.loads(path.read_text())
        valid = isinstance(values, dict) and all(
            isinstance(values.get(key), str) and values[key].strip() for key in required
        )
    except (ValueError, OSError):
        valid = False
    if not valid:
        raise ValueError(
            "required provider credential is missing or malformed"
        ) from None
    return {key: values[key] for key in required}


def child_environment(
    preflight: PreparedPreflight,
    unit: Path,
    checkout: Path,
    credentials: dict[str, str],
) -> dict[str, str]:
    """Start from explicit locators; inherit no unrelated plugins or model cache."""
    return {
        "PATH": f"{checkout / '.venv/bin'}:/usr/local/bin:/usr/bin:/bin",
        "HOME": preflight.runner_home,
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "OMP_NUM_THREADS": "2",
        "MKL_NUM_THREADS": "2",
        "OPENBLAS_NUM_THREADS": "2",
        "SIDERIUS_GENERATED_LIBRARY_DIR": str(unit / "workspace/generated_library"),
        "SIDERIUS_CHAIN_WORKSPACE": str(unit / "workspace"),
        "SIDERIUS_CALIBRATION_DIR": str(unit / "calibration"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "safe.directory",
        "GIT_CONFIG_VALUE_0": str(checkout),
        **credentials,
    }


def append_event(unit: Path, event: str, **fields: object) -> None:
    descriptor = os.open(
        unit / "events.jsonl",
        os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "a") as stream:
        stream.write(
            json.dumps({"event": event, "epoch": time.time(), **fields}) + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())


def run_child(
    *,
    preflight: PreparedPreflight,
    unit: Path,
    checkout: Path,
    deadline: int,
    credentials: dict[str, str],
) -> int:
    remaining = deadline - time.time()
    if remaining <= 0:
        append_event(unit, "deadline_already_elapsed")
        return 0
    if (unit / "workspace/.chain_halted").exists():
        raise RuntimeError("permanent chain halt is preserved; diagnosis required")
    descriptor = os.open(
        unit / "chain.log",
        os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "ab", buffering=0) as output:
        child = subprocess.Popen(
            preflight.command,
            cwd=checkout,
            env=child_environment(preflight, unit, checkout, credentials),
            user=preflight.runner_uid,
            group=preflight.runner_gid,
            extra_groups=[],
            stdout=output,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        append_event(unit, "chain_start", pid=child.pid, deadline_epoch=deadline)
        try:
            result = child.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            append_event(unit, "deadline_stop")
            return 0
        append_event(unit, "chain_exit", returncode=result)
        return result


def launch(
    *, preflight: PreparedPreflight, unit: Path, checkout: Path, credential_file: Path
) -> int:
    if os.geteuid() != 0:
        raise PermissionError(
            "the trusted clock/credential supervisor must run as root"
        )
    credentials = read_credentials(credential_file, preflight.required_api_keys)
    if unit.is_symlink():
        raise ValueError("unit must not be a symlink")
    unit.mkdir(parents=True, exist_ok=True, mode=0o750)
    info = unit.stat()
    if info.st_uid != 0 or info.st_mode & 0o022:
        raise PermissionError(
            "unit directory must be operator-owned and not worker-writable"
        )
    os.chown(unit, 0, preflight.runner_gid)
    os.chmod(unit, 0o750)
    descriptor = os.open(
        unit / ".supervisor.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        record = read_clock(unit / "launch.json")
        if record is None:
            if set(unit.iterdir()) != {unit / ".supervisor.lock"}:
                raise ValueError("fresh unit must contain no previous artifacts")
            record = create_clock(
                unit / "launch.json",
                preflight=preflight.model_dump(mode="json"),
                started=int(time.time()),
            )
        elif PreparedPreflight.model_validate(record.preflight) != preflight:
            raise ValueError("resume inputs differ from the immutable launch record")
        for name in ("workspace", "calibration"):
            path = unit / name
            if path.is_symlink():
                raise ValueError("runtime directory must not be a symlink")
            path.mkdir(mode=0o700, exist_ok=True)
            os.chown(path, preflight.runner_uid, preflight.runner_gid)
        return run_child(
            preflight=preflight,
            unit=unit,
            checkout=checkout,
            deadline=record.deadline_epoch,
            credentials=credentials,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--siderius-checkout", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--unit-dir", type=Path, required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--runner", required=True)
    parser.add_argument("--credential-file", type=Path)
    parser.add_argument("--launch", action="store_true")
    args = parser.parse_args()
    if args.unit_dir.is_symlink():
        parser.error("unit must not be a symlink")
    preflight = resolve_preflight(
        experiment=args.experiment.resolve(),
        checkout=args.siderius_checkout.resolve(),
        data=args.data_dir.resolve(),
        unit=args.unit_dir.resolve(),
        run_name=args.run_name,
        runner=args.runner,
    )
    if not args.launch:
        print(preflight.model_dump_json(indent=2))
        return
    if args.credential_file is None:
        parser.error("--launch requires a protected --credential-file")
    raise SystemExit(
        launch(
            preflight=preflight,
            unit=args.unit_dir.resolve(),
            checkout=args.siderius_checkout.resolve(),
            credential_file=args.credential_file,
        )
    )


if __name__ == "__main__":
    main()
