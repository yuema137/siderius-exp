"""Launch one numeric validation worker using operator-owned confinement argv.

The caller provisions read-only mounts, task-free filesystem visibility, network
isolation and the outer process-group deadline. This helper does not infer a
sandbox from a path or accept research-side launch commands. Empty prefixes are
only suitable for synthetic component tests, never private-data deployment.
"""

import os
import subprocess
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import torch

from experiments.shared.builtin_objective_worker import BuiltinObjectiveWorkerConfig
from experiments.shared.epoch_model_worker import EpochModelWorkerConfig
from experiments.shared.reviewed_objective_worker import ObjectiveWorkerConfig
from experiments.shared.validation_module_peer import ModulePeer


@dataclass(frozen=True)
class ValidationWorkerProcess:
    peer: ModulePeer
    pid: int
    startup_seconds: float


@contextmanager
def launch_validation_worker(
    config: EpochModelWorkerConfig
    | ObjectiveWorkerConfig
    | BuiltinObjectiveWorkerConfig,
    *,
    python: Path,
    cwd: Path,
    config_path: Path,
    stderr_path: Path,
    environment: Mapping[str, str],
    confinement_prefix: Sequence[str],
) -> Iterator[ValidationWorkerProcess]:
    """Pass snapshot and read-only config FDs; reserve stdout for protocol.

    The host config path need not be mounted into the worker. Files are new,
    owner-only and retained for diagnostics;
    stderr may contain private details and must stay in the protected job folder.
    Do not reuse file names across workers, epochs or concurrent jobs.
    """
    if type(config) is EpochModelWorkerConfig:
        module = "experiments.shared.epoch_model_worker"
    elif type(config) is BuiltinObjectiveWorkerConfig:
        module = "experiments.shared.builtin_objective_worker"
    elif type(config) is ObjectiveWorkerConfig:
        module = "experiments.shared.reviewed_objective_worker"
    else:
        raise TypeError("unsupported numeric worker configuration")
    if config.state_fd is None:
        raise ValueError("epoch worker requires an inherited snapshot descriptor")
    deadline = time.monotonic() + max(0.0, config.deadline_epoch - time.time())
    if time.monotonic() >= deadline:
        raise TimeoutError("numeric worker deadline exhausted before launch")
    # O_EXCL prevents overwriting another branch's config or following a symlink.
    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(config.model_dump_json())
    error_fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    process = None
    started = time.perf_counter()
    with os.fdopen(error_fd, "wb") as errors, config_path.open("rb") as config_input:
        try:
            process = subprocess.Popen(
                [
                    *confinement_prefix,
                    str(python),
                    "-B",
                    "-m",
                    module,
                    "--config-fd",
                    str(config_input.fileno()),
                ],
                cwd=cwd,
                env=dict(environment),
                pass_fds=(config.state_fd, config_input.fileno()),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
            )
            assert process.stdin is not None and process.stdout is not None
            peer = ModulePeer(
                input_fd=process.stdin.fileno(),
                output_fd=process.stdout.fileno(),
                device=torch.device(config.device),
                deadline=deadline,
                max_frame_bytes=config.max_frame_bytes,
            )
            yield ValidationWorkerProcess(
                peer, process.pid, time.perf_counter() - started
            )
            process.stdin.close()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("numeric worker deadline exhausted during shutdown")
            if process.wait(timeout=min(2.0, remaining)) != 0:
                raise RuntimeError("numeric worker exited unsuccessfully")
        finally:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=2)
                for stream in (process.stdin, process.stdout):
                    if stream is not None:
                        stream.close()
