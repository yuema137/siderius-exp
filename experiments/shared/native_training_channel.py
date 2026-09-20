"""An inherited channel tied to an operator-launched native training process.

This helper runs in the deployment launcher, never the coding-agent process.
It creates no listening socket. The deployment supplies the fixed interpreter,
entrypoint, sanitized environment and confinement prefix from protected policy.
The channel identifies that invocation; it does not prove arbitrary model code
honestly performed optimization or authorize private data by itself.
"""

import os
import socket
import subprocess
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path

from execute_tools.validation_execution import ValidationDeployment

from experiments.shared.epoch_model_worker import EpochModelSource
from experiments.shared.native_loss_binding import AdmittedLossSource


@dataclass(frozen=True)
class NativeTrainingChannel:
    process: subprocess.Popen
    channel: socket.socket


def native_channel_command(
    command: Sequence[str],
    *,
    python: Path,
    entrypoint: Path,
    deployment: ValidationDeployment,
    channel_fd: int,
) -> list[str]:
    """Replace research-selected validation settings with launcher-owned ones.

    Exact executable paths are intentional. The operator is responsible for
    their immutable content and task/path admission, not this string check.
    Native argparse remains the single owner of native option syntax.
    """
    if list(command[:2]) != [str(python), str(entrypoint)]:
        raise ValueError("invocation must use the deployment's native entrypoint")
    if channel_fd < 0:
        raise ValueError("training channel descriptor is invalid")
    arguments = list(command[2:])
    flag = "--validation_executor_json"
    positions = [
        i
        for i, value in enumerate(arguments)
        if value == flag or value.startswith(flag + "=")
    ]
    if len(positions) != 1:
        raise ValueError("native launch requires exactly one validation binding")
    position = positions[0]
    if arguments[position] == flag:
        if position + 1 >= len(arguments):
            raise ValueError("validation binding has no value")
        del arguments[position : position + 2]
    else:
        del arguments[position]
    settings = {**deployment.settings, "channel_fd": channel_fd}
    trusted = ValidationDeployment(factory=deployment.factory, settings=settings)
    return [str(python), str(entrypoint), *arguments, flag, trusted.model_dump_json()]


@contextmanager
def launch_native_training_channel(
    command: Sequence[str],
    *,
    python: Path,
    entrypoint: Path,
    deployment: ValidationDeployment,
    environment: Mapping[str, str],
    confinement_prefix: Sequence[str] = (),
    cwd: Path,
    entry_module: str | None = None,
    model_source: EpochModelSource | None = None,
    loss_source: AdmittedLossSource | None = None,
) -> Iterator[NativeTrainingChannel]:
    """Pass one private endpoint to one child; keep the outer watchdog's group.

    A confinement prefix must explicitly preserve the inherited descriptor and
    restrict candidate access to other processes/files. Empty is useful only
    for component tests. The caller owns the continuing deadline, event loop,
    whole-group cancellation and protected training record. When entry_module
    is supplied by policy, enter that module from the protected cwd rather than
    invoking a file (so deployment clients remain importable). On exit this helper
    closes the channel and reaps the direct child; it is not a group supervisor.
    """
    if (
        model_source is not None or loss_source is not None
    ) and entry_module != "experiments.shared.native_training_entry":
        raise ValueError("admitted source requires the native deployment entry module")
    sources = ExitStack()
    parent, child = socket.socketpair()
    process = None
    try:
        argv = native_channel_command(
            command,
            python=python,
            entrypoint=entrypoint,
            deployment=deployment,
            channel_fd=child.fileno(),
        )
        inherited = [child.fileno()]
        source_flags = []
        for flag, declaration in (
            ("--admitted-model-source-fd", model_source),
            ("--admitted-loss-source-fd", loss_source),
        ):
            if declaration is None:
                continue
            source = sources.enter_context(tempfile.TemporaryFile())  # noqa: SIM115 -- ExitStack owns the file
            payload = declaration.model_dump_json().encode()
            if len(payload) > 4194304:
                raise ValueError("admitted source exceeds limit")
            source.write(payload)
            source.flush()
            source.seek(0)
            descriptor = os.open(f"/proc/self/fd/{source.fileno()}", os.O_RDONLY)
            sources.callback(os.close, descriptor)
            inherited.append(descriptor)
            source_flags.extend([flag, str(descriptor)])
        if entry_module is not None:
            argv = [str(python), "-m", entry_module, *source_flags, *argv[2:]]
        process = subprocess.Popen(
            [*confinement_prefix, *argv],
            cwd=cwd,
            env=dict(environment),
            pass_fds=tuple(inherited),
        )
        child.close()
        yield NativeTrainingChannel(process, parent)
    finally:
        sources.close()
        child.close()
        parent.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
