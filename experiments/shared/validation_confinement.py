"""Operator-owned Linux namespace layout for native and numeric subprocesses.

This is an argv builder, not a caller authorization endpoint. Only protected
policy may choose mounts, identities and network access. It mounts no host root
implicitly and never receives private validation data paths from a researcher.
"""

import os
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NamespaceMount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: Path
    target: Path
    mode: Literal["read", "write", "device"] = "read"

    @model_validator(mode="after")
    def absolute_paths(self) -> Self:
        if not self.source.is_absolute() or not self.target.is_absolute():
            raise ValueError("namespace mounts require absolute paths")
        return self


class ValidationNamespace(BaseModel):
    """Explicit layout; existing ownership must allow the selected identity access.

    Numeric workers have no network. A native training deployment may explicitly
    retain networking where its experiment allows it. UID/GID changes require
    an appropriately privileged launcher and do not change host file ownership.
    The outer run supervisor remains responsible for deadlines and group cleanup.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    bubblewrap: Path
    cwd: Path
    mounts: tuple[NamespaceMount, ...]
    hidden_directories: tuple[Path, ...] = ()
    share_network: bool = False
    uid: int | None = Field(default=None, gt=0)
    gid: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def complete_policy(self) -> Self:
        if (self.uid is None) != (self.gid is None):
            raise ValueError("namespace identity requires both UID and GID")
        if any(
            not path.is_absolute()
            for path in (self.bubblewrap, self.cwd, *self.hidden_directories)
        ):
            raise ValueError("namespace policy requires absolute paths")
        return self

    def prefix(self) -> tuple[str, ...]:
        """Build a shell-free prefix, preserving explicitly inherited descriptors."""
        argv = [
            str(self.bubblewrap),
            "--die-with-parent",
            "--new-session",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            *(("--perms", "1777") if self.uid is not None else ()),
            "--tmpfs",
            "/tmp",
        ]
        if self.uid is None:
            argv.extend(("--unshare-all", "--cap-drop", "ALL"))
            if self.share_network:
                argv.append("--share-net")
        else:
            if os.geteuid() != 0:
                raise PermissionError(
                    "host identity switching requires root coordinator"
                )
            # Do not create a one-ID user namespace: --uid there only renames
            # coordinator root and cannot access the research account's files.
            argv.extend(
                (
                    "--unshare-ipc",
                    "--unshare-pid",
                    "--unshare-uts",
                    "--unshare-cgroup-try",
                )
            )
            if not self.share_network:
                argv.append("--unshare-net")
        # bwrap's implicit bind parents may be mode0700 and owned by the
        # coordinator. Create only synthetic namespace parents explicitly;
        # never chmod a host mount or expose its host parent directory.
        targets = tuple(mount.target for mount in self.mounts)
        parents = {parent for target in targets for parent in target.parents}
        for parent in sorted(parents, key=lambda path: (len(path.parts), str(path))):
            if parent in {Path("/"), Path("/tmp"), Path("/proc"), Path("/dev")}:
                continue
            if any(parent == target or target in parent.parents for target in targets):
                continue
            argv.extend(("--dir", str(parent)))
        for mount in self.mounts:
            flag = {"read": "--ro-bind", "write": "--bind", "device": "--dev-bind"}[
                mount.mode
            ]
            argv.extend((flag, str(mount.source), str(mount.target)))
        for path in self.hidden_directories:
            argv.extend(("--tmpfs", str(path)))
        # These caches must work even when no host passwd database is mounted.
        for key, value in (
            ("HOME", "/tmp"),
            ("TORCHINDUCTOR_CACHE_DIR", "/tmp/torchinductor"),
            ("TRITON_CACHE_DIR", "/tmp/triton"),
            ("CUDA_CACHE_PATH", "/tmp/cuda-cache"),
        ):
            argv.extend(("--setenv", key, value))
        argv.extend(("--chdir", str(self.cwd), "--"))
        if self.uid is not None:
            # Mount setup needs privilege. Drop host credentials and every
            # capability before executing any candidate Python/code. setpriv
            # preserves the explicitly inherited validation/config descriptors.
            argv.extend(
                (
                    "/usr/bin/setpriv",
                    f"--reuid={self.uid}",
                    f"--regid={self.gid}",
                    "--clear-groups",
                    "--bounding-set=-all",
                    "--inh-caps=-all",
                    "--ambient-caps=-all",
                    "--no-new-privs",
                    "--",
                )
            )
        return tuple(argv)
