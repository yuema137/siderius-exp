"""Protected per-invocation entry boundary for a deployment-owned native runner.

The installed root-owned wrapper must fix the policy path and enter this module
from its protected checkout with isolated Python. Never allow the research caller
to select a handler, policy, Python path or coordinator environment.
"""

import importlib
import os
import stat
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, JsonValue, StrictInt

# Only native source/workspace locators are forwarded as untrusted data. These
# never become coordinator environment variables, mount declarations or policy.
_SOURCE_ENVIRONMENT_KEYS = (
    "SIDERIUS_PLUGIN_DIRS",
    "SIDERIUS_LOSS_DIRS",
    "SIDERIUS_GENERATED_LIBRARY_DIR",
    "SIDERIUS_CHAIN_WORKSPACE",
    "SIDERIUS_TASK_CODE_MANIFEST",
    "SIDERIUS_TASK_CODE_SHA256",
)


class NativeLauncherPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    caller_uid: Annotated[StrictInt, Field(gt=0)]
    caller_gid: Annotated[StrictInt, Field(ge=0)]
    coordinator_uid: Annotated[StrictInt, Field(ge=0)] = 0
    cwd: Path
    handler: str = Field(
        pattern=r"^experiments\.[a-zA-Z_][a-zA-Z0-9_.]*:[a-zA-Z_][a-zA-Z0-9_]*$"
    )
    settings: dict[str, JsonValue]
    environment: dict[str, str]
    deadline_epoch: FiniteFloat


@dataclass(frozen=True)
class NativeLaunchContext:
    caller_uid: int
    caller_gid: int
    source_cwd: Path
    deadline: float
    policy: NativeLauncherPolicy
    source_environment: Mapping[str, str] = field(default_factory=dict)


def read_launcher_policy(path: Path, *, owner_uid: int) -> NativeLauncherPolicy:
    """Read a bounded regular policy from an operator-owned directory chain."""
    if not path.is_absolute():
        raise ValueError("launcher policy path must be absolute")
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, owner_uid}:
            raise PermissionError("launcher policy parents must be operator-owned")
        if info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX:
            raise PermissionError("launcher policy parent is writable by other users")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != owner_uid
            or info.st_mode & 0o022
            or info.st_nlink != 1
        ):
            raise PermissionError(
                "launcher policy must be an operator-owned regular file"
            )
        payload = stream.read(1048577)
    if len(payload) > 1048576:
        raise ValueError("launcher policy exceeds size limit")
    return NativeLauncherPolicy.model_validate_json(payload)


def authorize_native_caller(
    policy: NativeLauncherPolicy,
    *,
    effective_uid: int,
    environment: Mapping[str, str],
    source_cwd: Path,
    now_epoch: float,
    now_monotonic: float,
) -> NativeLaunchContext:
    """Use sudo-issued identity only after checking coordinator privilege."""
    if effective_uid != policy.coordinator_uid or effective_uid == policy.caller_uid:
        raise PermissionError(
            "native launcher requires its separate coordinator account"
        )
    try:
        caller = int(environment["SUDO_UID"])
        group = int(environment["SUDO_GID"])
    except (KeyError, ValueError) as exc:
        raise PermissionError(
            "native launcher requires sudo-issued caller identity"
        ) from exc
    if (caller, group) != (policy.caller_uid, policy.caller_gid):
        raise PermissionError("native launcher caller is not assigned to this run")
    remaining = policy.deadline_epoch - now_epoch
    if remaining <= 0:
        raise TimeoutError("native run deadline exhausted before admission")
    if not policy.cwd.is_absolute() or not source_cwd.is_absolute():
        raise ValueError(
            "native coordinator and source working directories must be absolute"
        )
    return NativeLaunchContext(
        caller_uid=caller,
        caller_gid=group,
        source_cwd=source_cwd,
        deadline=now_monotonic + remaining,
        policy=policy,
        source_environment={
            key: environment[key]
            for key in _SOURCE_ENVIRONMENT_KEYS
            if key in environment
        },
    )


def dispatch_native_training(policy_path: Path, command: Sequence[str]) -> int:
    """Dispatch only a fixed policy's handler; it owns capture and native execution.

    argv and the original cwd remain untrusted research inputs. The handler must
    capture/admit them before executing native code and must establish child
    namespaces/UIDs. This entry never runs the research command as coordinator.
    """
    policy = read_launcher_policy(policy_path, owner_uid=os.geteuid())
    context = authorize_native_caller(
        policy,
        effective_uid=os.geteuid(),
        environment=os.environ,
        source_cwd=Path.cwd(),
        now_epoch=time.time(),
        now_monotonic=time.monotonic(),
    )
    if not command or sum(len(arg.encode()) for arg in command) > 1048576:
        raise ValueError("native command is empty or exceeds request limit")
    os.chdir(policy.cwd)
    # This function runs in a dedicated disposable coordinator process. A caller's
    # HOME, plugin roots, Python overlays and provider credentials are not policy.
    os.environ.clear()
    os.environ.update(policy.environment)
    module, symbol = policy.handler.split(":")
    handler = getattr(importlib.import_module(module), symbol)
    result = handler(context, tuple(command))
    if type(result) is not int or not 0 <= result <= 255:
        raise ValueError("native handler did not return a process exit status")
    return result
