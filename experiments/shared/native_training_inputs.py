"""Capture native inputs before protected launch without importing plugins.

The operator supplies readable research/public roots and a protected destination.
This freezes bytes and CLI interpretation; it does not authenticate a caller or
approve a task manifest, model, objective, data scope or output path.
"""

import hashlib
import json
import os
import shutil
import stat
import tempfile
from collections.abc import Sequence
from pathlib import Path

from agent.schemas.data_analysis.common import Sha256
from execute_tools.training_cli import build_training_parser
from pydantic import BaseModel, ConfigDict

# These native inputs contain values, not paths resolved relative to their own
# location. In particular, task_manifest must retain its operator-approved path
# and composition-relative semantics; it is admitted separately by the launcher.
_INPUTS = (
    "model_cfg",
    "train_cfg",
    "loss_cfg",
    "custom_loss_contract_json",
    "model_io_json",
    "dataset_profile_json",
    "sample_set_json",
    "eval_sample_set_json",
    "task_scope_ref",
    "task_eval_scope_ref",
    "file_order_json",
    "runtime_policy_json",
)
_OPAQUE_SCOPES = {"task_scope_ref", "task_eval_scope_ref"}


class NativeInputFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    argument: str
    original: Path
    captured: Path
    sha256: Sha256


class CapturedNativeInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    command: tuple[str, ...]
    root: Path
    files: tuple[NativeInputFile, ...]


def _read_allowed_input(path: Path, roots: Sequence[Path], *, max_bytes: int) -> bytes:
    """Walk below an allowed root by directory FDs; never follow a changed link."""
    resolved = path.resolve(strict=True)
    for root in roots:
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            continue
        if not relative.parts:
            raise ValueError("native JSON input must be a file")
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in relative.parts[:-1]:
                child = os.open(
                    part,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=descriptor,
                )
                os.close(descriptor)
                descriptor = child
            child = os.open(
                relative.parts[-1],
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=descriptor,
            )
            with os.fdopen(child, "rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                    raise ValueError(
                        "native JSON input must be a regular file with one hard link"
                    )
                payload = stream.read(max_bytes + 1)
                after = os.fstat(stream.fileno())
                if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size,
                    after.st_mtime_ns,
                    after.st_ctime_ns,
                ):
                    raise ValueError("native JSON input changed during capture")
        finally:
            os.close(descriptor)
        if len(payload) > max_bytes:
            raise ValueError("native JSON input exceeds configured capture limit")
        return payload
    raise PermissionError("native JSON input lies outside operator-selected roots")


def capture_native_training_inputs(
    command: Sequence[str],
    *,
    python: Path,
    entrypoint: Path,
    source_cwd: Path,
    allowed_roots: Sequence[Path],
    parent: Path,
    owner_uid: int,
    max_file_bytes: int,
) -> CapturedNativeInputs:
    """Freeze effective input files and append native-parser-equivalent overrides.

    Native argparse owns repeated/abbreviated/equals-form flags and defaults.
    Capture their final effective values, then append canonical captured paths.
    All other arguments retain their existing interpretation. The launcher must
    separately admit task manifest/data/output/environment/code paths before
    executing this command. Only mount this capture read-only into children.
    """
    if list(command[:2]) != [str(python), str(entrypoint)]:
        raise ValueError("invocation must use the deployment's native entrypoint")
    if max_file_bytes <= 0:
        raise ValueError("native input capture requires a positive size limit")
    info = parent.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != owner_uid
        or info.st_mode & 0o022
        or os.geteuid() != owner_uid
    ):
        raise PermissionError("native input parent must be operator-owned")
    roots = tuple(root.resolve(strict=True) for root in allowed_roots)
    try:
        args = build_training_parser().parse_args(command[2:])
    except SystemExit as error:
        raise ValueError("invalid native training arguments") from error
    payloads = []
    for name in _INPUTS:
        value = getattr(args, name)
        if value is not None:
            path = Path(value)
            original = path if path.is_absolute() else source_cwd / path
            payload = _read_allowed_input(original, roots, max_bytes=max_file_bytes)
            # Scope serialization belongs to the task; it need not be JSON.
            if name not in _OPAQUE_SCOPES:
                json.loads(payload)
            payloads.append((name, original, payload))
    root = Path(tempfile.mkdtemp(prefix="native-inputs-", dir=parent))
    try:
        argv = list(command)
        files = []
        for name, original, payload in payloads:
            captured = root / f"{name}.json"
            with captured.open("xb") as stream:
                stream.write(payload)
            captured.chmod(0o444)
            files.append(
                NativeInputFile(
                    argument=name,
                    original=original,
                    captured=captured,
                    sha256=hashlib.sha256(payload).hexdigest(),
                )
            )
            argv.extend((f"--{name}", str(captured)))
        result = CapturedNativeInputs(
            command=tuple(argv), root=root, files=tuple(files)
        )
        root.chmod(0o555)
        return result
    except BaseException:
        root.chmod(0o700)
        shutil.rmtree(root)
        raise
