"""Check a drafted launcher policy before the coordinator reads it under sudo.

A root-owned wrapper reads the policy as the coordinator, so every mistake
in it surfaces as a permission error or as a run against the wrong task
with the clock already going. This checks what can be checked from the
operator's seat: the framework's own model, the task binding, the manifests
by digest, and the three things a drafted policy has actually got wrong so
far — the native entrypoint, the protected `cwd`, and empty namespaces.

`--installed` adds the ownership and parent-chain rules `read_launcher_policy`
enforces, which only mean anything once the file is at the path the launcher
reads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

from experiments.phyts_tess.main_orchestrator.native_handler import TessNativePolicy
from experiments.phyts_tess.main_orchestrator.public_data_path import (
    PUBLIC_TESS_TASK_ID,
)
from experiments.shared.native_launcher import NativeLauncherPolicy
from experiments.shared.native_runtime import NativeRuntimePolicy
from experiments.shared.validation_confinement import ValidationNamespace

__all__ = ["EXPECTED_HANDLER", "TRAINING_ENTRYPOINT", "verify_launcher_policy"]

EXPECTED_HANDLER = "experiments.phyts_tess.main_orchestrator.native_handler:run"

#: The exact `argv[1]` the tuner's sandbox emits for training
#: (`core/sandbox_executor.py`, `child_script_path("execute_tools/train_engine_sandbox.py")`).
#: `capture_native_training_inputs` refuses any invocation whose first two
#: arguments are not `[runtime.python, runtime.entrypoint]`, so a policy that
#: names any other file refuses every real launch — with the same message the
#: authorization probe treats as its PASS.
TRAINING_ENTRYPOINT = Path("execute_tools") / "train_engine_sandbox.py"

#: What the protected relaunch imports from `policy.cwd`
#: (`python -m experiments.shared.native_training_entry`).
NATIVE_ENTRY_MODULE = Path("experiments") / "shared" / "native_training_entry.py"


def _verify_installed_ownership(path: Path, coordinator_uid: int) -> None:
    """Mirror `read_launcher_policy`'s file checks at their real location.

    The launcher reads the policy with `owner_uid=os.geteuid()`, and the
    wrapper runs as the COORDINATOR — so the installed file must be owned by
    that account, not by root. Installing it root-owned looks right, passes
    every content check, and fails at the caller's first invocation with
    "launcher policy must be an operator-owned regular file".

    Parents may be root or the coordinator, which is why `/etc/tess-native`
    being root-owned is fine while the file itself being root-owned is not.
    """
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{path} is not a regular file")
    if info.st_uid != coordinator_uid:
        raise ValueError(
            f"{path} is owned by uid {info.st_uid}; the launcher reads it as "
            f"the coordinator ({coordinator_uid}) and requires that owner. "
            f"Fix with: sudo chown {coordinator_uid} {path}"
        )
    if info.st_mode & 0o022:
        raise ValueError(f"{path} is writable by group or other")
    if info.st_nlink != 1:
        raise ValueError(f"{path} has {info.st_nlink} hard links; expected 1")

    for parent in path.parents:
        parent_info = parent.lstat()
        if parent_info.st_uid not in {0, coordinator_uid}:
            raise ValueError(
                f"{parent} is owned by uid {parent_info.st_uid}; every parent "
                "must be root or the coordinator"
            )
        if parent_info.st_mode & 0o022 and not parent_info.st_mode & stat.S_ISVTX:
            raise ValueError(f"{parent} is writable by other users")


def _exposed(path: Path, namespace: ValidationNamespace) -> bool:
    """Whether a host path is visible inside the namespace through some mount."""
    resolved = path.resolve()
    for mount in namespace.mounts:
        source = mount.source.resolve()
        if resolved == source or source in resolved.parents:
            return True
    return False


def _covered_by(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _exposed_literally(path: Path, namespace: ValidationNamespace) -> bool:
    """Whether the path, spelled exactly as given, exists inside the namespace.

    bwrap resolves a symlink chain INSIDE the namespace, so a hop that names a
    linked directory must be bound under that literal name; resolving it
    first, as `_exposed` does, would pass while the exec fails.
    """
    return any(
        path == mount.target or mount.target in path.parents
        for mount in namespace.mounts
    )


def _link_hops(path: Path) -> list[Path]:
    hops = [path]
    while hops[-1].is_symlink() and len(hops) < 40:
        target = Path(os.readlink(hops[-1]))
        hops.append(target if target.is_absolute() else hops[-1].parent / target)
    return hops


def _verify_runtime(runtime: NativeRuntimePolicy, cwd: Path) -> None:
    """The three drafting mistakes that verify fine and refuse every launch."""
    if not runtime.python.is_file():
        raise ValueError(f"runtime.python is not a file: {runtime.python}")
    if runtime.entrypoint.parts[-2:] != TRAINING_ENTRYPOINT.parts or (
        not runtime.entrypoint.is_file()
    ):
        raise ValueError(
            f"runtime.entrypoint is {runtime.entrypoint}; it must be the "
            f"framework's {TRAINING_ENTRYPOINT}, the exact script the tuner "
            "launches training with — capture refuses any other argv[1]"
        )
    entry = cwd / NATIVE_ENTRY_MODULE
    if not entry.is_file():
        raise ValueError(
            f"policy.cwd is {cwd}, but the protected relaunch runs "
            "`python -m experiments.shared.native_training_entry` from there and "
            f"{entry} does not exist; point cwd at the published runtime root"
        )
    required = [runtime.python, runtime.entrypoint, entry, cwd, *runtime.readable_roots]
    readable = [root.resolve() for root in runtime.readable_roots]
    for mount in runtime.training_namespace.mounts:
        if mount.mode == "write" and not _covered_by(mount.source.resolve(), readable):
            raise ValueError(
                f"training_namespace writes to {mount.source}, which is not a readable "
                "root; capture resolves the tuner's config files and plugin source "
                "against readable_roots, so every launch from there would be refused"
            )
    for label in ("probe", "training", "worker"):
        namespace: ValidationNamespace = getattr(runtime, f"{label}_namespace")
        if not namespace.mounts:
            raise ValueError(
                f"{label}_namespace declares no mounts; bubblewrap mounts no host "
                "root implicitly, so the child would see only /proc, /dev and /tmp"
            )
        hidden = [str(path) for path in required if not _exposed(path, namespace)]
        if hidden:
            raise ValueError(
                f"{label}_namespace does not expose {hidden[:3]}; the child needs "
                "the interpreter, the training script, the entry module's root "
                "and every readable root"
            )
        binds_gpu = any(
            mount.mode == "device" and mount.target.name.startswith("nvidia")
            for mount in namespace.mounts
        )
        if binds_gpu and not _exposed_literally(Path("/sys"), namespace):
            raise ValueError(
                f"{label}_namespace binds NVIDIA device nodes but not /sys; the "
                "driver reads the PCI device list there, and without it "
                "cudaGetDeviceCount fails with `Error 304: OS call failed`"
            )
        unlinked = [
            str(hop)
            for hop in _link_hops(runtime.python)
            if not _exposed_literally(hop, namespace)
        ]
        if unlinked:
            raise ValueError(
                f"{label}_namespace does not expose the interpreter's symlink hop "
                f"{unlinked[0]}; bwrap resolves the chain inside the namespace, so "
                "`execvp … No such file or directory` follows even though the "
                "final file is mounted"
            )


def verify_launcher_policy(path: Path, *, installed: bool = False) -> dict[str, object]:
    """Validate a policy; raise on the first thing that is wrong."""
    path = Path(path)
    draft = json.loads(path.read_text(encoding="utf-8"))

    # The framework's model owns uid, gid, cwd, deadline and handler shape.
    policy = NativeLauncherPolicy.model_validate(draft)
    if policy.handler != EXPECTED_HANDLER:
        raise ValueError(
            f"policy dispatches {policy.handler!r}; this deployment is "
            f"{EXPECTED_HANDLER!r}"
        )
    # Restated from `authorize_native_caller`, because a policy that cannot
    # authorize is better caught here than under sudo with a clock running.
    if policy.coordinator_uid == policy.caller_uid:
        raise ValueError(
            "coordinator and caller share a uid; the launcher requires a "
            "separate coordinator account and will refuse this policy"
        )

    settings = TessNativePolicy.model_validate(policy.settings)
    if settings.task_data_path_id != PUBLIC_TESS_TASK_ID:
        raise ValueError(
            f"settings publish adapter {settings.task_data_path_id!r}; this "
            f"deployment publishes {PUBLIC_TESS_TASK_ID!r}"
        )

    manifest = settings.manifest
    if not manifest.is_file():
        raise ValueError(f"task manifest is missing at {manifest}")
    observed = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if observed != settings.manifest_sha256:
        raise ValueError(
            f"task manifest digest is {observed}, policy pins "
            f"{settings.manifest_sha256}; the manifest changed after drafting"
        )

    for label, directory in (
        ("agent_view", settings.agent_view),
        ("validation_data", settings.validation_data),
    ):
        if not directory.is_dir():
            raise ValueError(f"{label} is not a directory: {directory}")

    # `build_views.py` writes `agent/` and `evaluator/` as siblings, which is
    # right while the operator holds both and wrong once one of them is what
    # the caller reads. Finding them still adjacent means the views were
    # handed over as produced.
    beside = settings.agent_view.parent / "evaluator"
    if beside.is_dir():
        raise ValueError(
            f"the evaluator view is still beside the agent view at {beside}; "
            "build_views.py writes them as siblings, and they must be "
            "separated before one of them becomes the caller's"
        )

    truth = settings.truth_manifest
    if not truth.is_file():
        raise ValueError(f"truth manifest is missing at {truth}")
    truth_digest = hashlib.sha256(truth.read_bytes()).hexdigest()
    if truth_digest != settings.truth_manifest_sha256:
        raise ValueError(
            f"truth manifest digest is {truth_digest}, policy pins "
            f"{settings.truth_manifest_sha256}; the manifest changed after drafting"
        )
    if truth.resolve().is_relative_to(settings.agent_view.resolve()):
        raise ValueError(
            f"truth manifest {truth} sits inside the agent view; the caller "
            "would be reading validation targets"
        )

    _verify_runtime(settings.runtime, policy.cwd)

    if installed:
        _verify_installed_ownership(path, policy.coordinator_uid)

    return {
        "installed_checks": installed,
        "handler": policy.handler,
        "caller_uid": policy.caller_uid,
        "coordinator_uid": policy.coordinator_uid,
        "task_data_path_id": settings.task_data_path_id,
        "manifest": str(manifest),
        "manifest_sha256": observed,
        "truth_manifest": str(truth),
        "truth_manifest_sha256": truth_digest,
        "agent_view": str(settings.agent_view),
        "entrypoint": str(settings.runtime.entrypoint),
        "cwd": str(policy.cwd),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", type=Path)
    parser.add_argument(
        "--installed",
        action="store_true",
        help="also verify ownership and the parent chain at this exact path",
    )
    args = parser.parse_args(argv)
    print(
        json.dumps(
            verify_launcher_policy(args.policy, installed=args.installed), indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
