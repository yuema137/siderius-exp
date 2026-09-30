"""Draft the launcher policy from the deployment itself, never by hand.

The first policy was written by hand and verified, and it named the wrong
native entrypoint and three empty namespaces — mistakes a reader cannot see
and a real launch refuses. Every value below that can be derived from the
deployment is derived from it: the interpreter, the training script the
framework will actually emit, the three pinned digests (asked of the
deployment's own interpreter), the manifests' digests, and a mount list
built from what the child needs to see.

What the operator still supplies is what only the operator knows: the two
account ids, where the caller's writable workspace is, the device, and the
window. `stage_policy.py` restamps the deadline right before installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from experiments.phyts_tess.main_orchestrator.verify_launcher_policy import (
    EXPECTED_HANDLER,
    NATIVE_ENTRY_MODULE,
    TRAINING_ENTRYPOINT,
    verify_launcher_policy,
)

__all__ = [
    "draft_launcher_policy",
    "interpreter_facts",
    "interpreter_mounts",
    "link_hops",
]

#: Host trees a Python process needs: the interpreter's shared libraries,
#: `ld.so.cache`, the CUDA driver library — and `/sys`, which the driver and
#: NVML read for the PCI device list; without it `cudaGetDeviceCount` fails
#: with `Error 304: OS call failed` even though every device node is bound
#: (observed on the first host probe). Read-only; those absent are skipped.
DEFAULT_SYSTEM_MOUNTS = ("/usr", "/lib", "/lib64", "/bin", "/sbin", "/etc", "/sys")

#: `--dev /dev` synthesizes a minimal /dev; the GPU nodes must be bound in.
#: Those absent on the host are skipped, and a policy drafted on a host
#: without them simply has no GPU inside the namespace.
DEFAULT_DEVICE_NODES = (
    "/dev/nvidia0",
    "/dev/nvidiactl",
    "/dev/nvidia-uvm",
    "/dev/nvidia-uvm-tools",
    "/dev/nvidia-modeset",
)

_MANIFEST = Path("composition.yaml")
_PROFILE = Path("tasks/phyts_tess/declared/dataset_profile.json")
_TRUTH = Path("tasks/phyts_tess/data/manifests/rotation_identity.csv")

_FACTS = """
import hashlib, json, sys
from pathlib import Path
import core.sandbox_executor as sandbox
from ml_models import loss_models_sandbox, models_sandbox
print(json.dumps({
    "executable": sys.executable,
    "siderius_root": sandbox.SIDERIUS_ROOT,
    "constructor_sha256": models_sandbox.registered_model_construction_implementation_sha256(),
    "builtin_model_sha256": hashlib.sha256(Path(models_sandbox.__file__).read_bytes()).hexdigest(),
    "builtin_objective_sha256": hashlib.sha256(Path(loss_models_sandbox.__file__).read_bytes()).hexdigest(),
}))
"""


def interpreter_facts(python: Path) -> dict[str, str]:
    """Ask the deployment's interpreter what it will run and what it pins.

    `SIDERIUS_ROOT` decides the training script's path, and the three
    digests are what `admit_model_source` and the builtin objective compare
    against; computing them anywhere else would pin a different checkout.
    """
    completed = subprocess.run(
        [str(python), "-c", _FACTS], capture_output=True, text=True, check=False
    )
    if completed.returncode:
        raise RuntimeError(
            f"{python} could not report deployment facts (exit "
            f"{completed.returncode}); it must be the framework venv's interpreter: "
            f"{completed.stderr[-2000:]}"
        )
    # Plugin loaders print progress lines on import; the facts are the last line.
    facts = json.loads(completed.stdout.strip().splitlines()[-1])
    return {key: str(value) for key, value in facts.items()}


def _mount(source: Path, mode: str = "read") -> dict[str, str]:
    return {"source": str(source), "target": str(source), "mode": mode}


def _covered(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def link_hops(path: Path) -> list[Path]:
    """`path` and every symlink target after it, each under its LITERAL path."""
    hops = [path]
    while hops[-1].is_symlink() and len(hops) < 40:
        target = Path(os.readlink(hops[-1]))
        hops.append(target if target.is_absolute() else hops[-1].parent / target)
    return hops


def _real_ancestor(path: Path) -> Path:
    """The deepest ancestor of `path` whose own path has no symlink component."""
    candidate = path.parent
    while candidate != candidate.parent and candidate.resolve() != candidate:
        candidate = candidate.parent
    return candidate


def interpreter_mounts(python: Path, exposed: list[Path]) -> list[Path]:
    """Roots to mount so the interpreter's whole symlink chain resolves inside.

    A hop whose literal path is not already exposed is served by its nearest
    ancestor free of symlink components, so the linked directory and the
    directory it points at both appear. The final interpreter gets its tree
    (`<root>/bin/python3.x` → `<root>`) so `lib/` comes along.
    """
    roots = list(exposed)
    added: list[Path] = []
    for hop in link_hops(python):
        if not _covered(hop, roots):
            root = _real_ancestor(hop)
            roots.append(root)
            added.append(root)
    final = link_hops(python)[-1].resolve()
    if not _covered(final, [root.resolve() for root in roots]):
        roots.append(final.parents[1])
        added.append(final.parents[1])
    return added


def _existing(paths: tuple[str, ...]) -> list[Path]:
    return [Path(path) for path in paths if Path(path).exists()]


def draft_launcher_policy(
    *,
    root: Path,
    data_dir: Path,
    caller_uid: int,
    caller_gid: int,
    coordinator_uid: int,
    caller_work: Path,
    device: str = "cuda:0",
    hours: float = 6.0,
    job_parent: Path = Path("/var/lib/tess-native"),
    bubblewrap: Path = Path("/usr/bin/bwrap"),
    max_snapshot_bytes: int = 268435456,
    system_mounts: tuple[str, ...] = DEFAULT_SYSTEM_MOUNTS,
    device_nodes: tuple[str, ...] = DEFAULT_DEVICE_NODES,
) -> dict[str, Any]:
    """The policy as a JSON-ready dict; nothing is written here."""
    root = root.resolve(strict=True)
    framework = root / "framework"
    python = framework / ".venv" / "bin" / "python"
    runtime = root / "runtime"
    caller_bundle = root / "bundle" / "caller"
    evaluator_bundle = root / "bundle" / "evaluator"
    agent_view = root / "views" / "agent"
    for label, path in (
        ("framework interpreter", python),
        ("published runtime", runtime / NATIVE_ENTRY_MODULE),
        ("caller composition", caller_bundle / _MANIFEST),
        ("dataset profile", caller_bundle / _PROFILE),
        ("truth manifest", evaluator_bundle / _TRUTH),
        ("agent view", agent_view / "manifests"),
        ("validation data", data_dir / "tess_rotation_val.npz"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{label} is missing: {path}")

    facts = interpreter_facts(python)
    entrypoint = Path(facts["siderius_root"]) / TRAINING_ENTRYPOINT
    if not entrypoint.is_file():
        raise FileNotFoundError(f"framework training script is missing: {entrypoint}")

    # The caller's work directory is a READABLE root as well as the training
    # namespace's one writable mount: capture resolves the tuner's own
    # `--model_cfg` / `--train_cfg` files and any generated plugin source
    # against `readable_roots`, and those live there. Without it every real
    # launch is refused at capture.
    work = caller_work.resolve()
    readable = [framework, runtime, caller_bundle, agent_view, data_dir.resolve(), work]
    read_mounts = [
        *(_mount(path) for path in _existing(system_mounts)),
        *(_mount(path) for path in readable if path != work),
    ]
    # The venv's python is a symlink chain into the deployment's own
    # interpreter tree, and bwrap resolves that chain INSIDE the namespace: every
    # hop must be visible under its literal path, not only the final file.
    for root in interpreter_mounts(
        python, [Path(item["source"]) for item in read_mounts]
    ):
        read_mounts.append(_mount(root))
    # Likewise the framework package root: the training script lives there,
    # and it is only under `framework/` when the venv is an editable install.
    siderius_root = Path(facts["siderius_root"]).resolve()
    if not _covered(
        siderius_root, [Path(item["source"]).resolve() for item in read_mounts]
    ):
        read_mounts.append(_mount(siderius_root))
    devices = [_mount(path, "device") for path in _existing(device_nodes)]

    def namespace(extra: list[dict[str, str]] = ()) -> dict[str, Any]:  # type: ignore[assignment]
        return {
            "bubblewrap": str(bubblewrap),
            "cwd": str(runtime),
            "mounts": [*read_mounts, *devices, *extra],
        }

    manifest = caller_bundle / _MANIFEST
    truth = evaluator_bundle / _TRUTH
    return {
        "caller_uid": caller_uid,
        "caller_gid": caller_gid,
        "coordinator_uid": coordinator_uid,
        # The protected relaunch is `python -m experiments.shared.native_training_entry`
        # from here; the published runtime is the root that module lives in.
        "cwd": str(runtime),
        "handler": EXPECTED_HANDLER,
        "environment": {},
        "deadline_epoch": time.time() + hours * 3600.0,
        "settings": {
            "runtime": {
                "python": str(python),
                "entrypoint": str(entrypoint),
                "readable_roots": [str(path) for path in readable],
                "job_parent": str(job_parent),
                "probe_namespace": namespace([_mount(work)]),
                # Training writes checkpoints and results into the caller's
                # sandbox; that is the one writable host path, and only here.
                "training_namespace": namespace([_mount(work, "write")]),
                "worker_namespace": namespace([_mount(work)]),
                "child_environment": {"PATH": "/usr/bin:/bin", "OMP_NUM_THREADS": "1"},
                "device": device,
                "constructor_sha256": facts["constructor_sha256"],
                "builtin_model_sha256": facts["builtin_model_sha256"],
                "builtin_objective_sha256": facts["builtin_objective_sha256"],
                "max_snapshot_bytes": max_snapshot_bytes,
            },
            "manifest": str(manifest),
            "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "profile": json.loads(
                (caller_bundle / _PROFILE).read_text(encoding="utf-8")
            ),
            "agent_view": str(agent_view),
            "truth_manifest": str(truth),
            "truth_manifest_sha256": hashlib.sha256(truth.read_bytes()).hexdigest(),
            "validation_data": str(data_dir.resolve()),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--caller-uid", type=int, required=True)
    parser.add_argument("--caller-gid", type=int, required=True)
    parser.add_argument("--coordinator-uid", type=int, required=True)
    parser.add_argument(
        "--caller-work",
        type=Path,
        required=True,
        help="the caller's writable workspace root; the only host path training may write",
    )
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--hours", type=float, default=6.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise FileExistsError(f"refusing to overwrite {args.out}")
    policy = draft_launcher_policy(
        root=args.deployment_root,
        data_dir=args.data_dir,
        caller_uid=args.caller_uid,
        caller_gid=args.caller_gid,
        coordinator_uid=args.coordinator_uid,
        caller_work=args.caller_work,
        device=args.device,
        hours=args.hours,
    )
    args.out.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verify_launcher_policy(args.out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
