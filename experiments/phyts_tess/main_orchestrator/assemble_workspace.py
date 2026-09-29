"""Assemble the caller's workspace: the toolkit payload plus three operator documents.

The toolkit's `ASSEMBLY.md` owns the rules; this is their executable form
for TESS. The payload (`AGENTS.md` and `.agents/skills/siderius-toolkit/`)
comes from the pinned framework checkout and is copied byte for byte; the
run declaration, task brief and treatment scope come from this repository.
An existing destination is refused rather than merged, a symlink in the
payload is refused rather than followed, every written file is re-read and
compared to its source, and the inventory is written OUTSIDE the workspace
so the operator's record is not part of what the agent reads.

Nothing here starts a clock, calls a provider or touches a protected root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

__all__ = ["PAYLOAD_RELATIVE", "assemble_workspace", "declared_run_id"]

PAYLOAD_RELATIVE = Path("docs/agent-reference/orchestrator-toolkit/payload")

#: Where each operator document lands, relative to the workspace root.
_DOCUMENTS = {
    "run_declaration": Path("SIDERIUS-RUN.md"),
    "task_brief": Path("task.md"),
    "treatment_scope": Path("TREATMENT_SCOPE.md"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_tree(source: Path, destination: Path) -> dict[str, str]:
    """Regular files only; a symlink anywhere in the payload is a policy question."""
    written: dict[str, str] = {}
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if path.is_symlink():
            raise ValueError(
                f"payload contains a symlink, which needs an explicit policy: {path}"
            )
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        if _sha256(target) != _sha256(path):
            raise RuntimeError(f"bytes changed while copying {relative}")
        written[str(relative)] = _sha256(target)
    return written


def _revision(checkout: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return completed.stdout.strip() or None


_RUN_ID = re.compile(
    r"^Run id \*\*`([A-Za-z0-9][A-Za-z0-9._-]{0,63})`\*\*", re.MULTILINE
)


def declared_run_id(run_declaration: Path) -> str:
    """The run id the declaration names in its first line, or a refusal."""
    match = _RUN_ID.search(run_declaration.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(
            f"{run_declaration} does not open with 'Run id **`<id>`**'; the run id "
            "must be declared where an operator sees it first"
        )
    return match.group(1)


def _instantiate(text: str, *, declared: str, run_id: str) -> str:
    """Retarget every occurrence of the declared run id, and nothing else."""
    if run_id == declared:
        return text
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", run_id):
        raise ValueError(f"invalid run id: {run_id!r}")
    return text.replace(declared, run_id)


def assemble_workspace(
    *,
    framework: Path,
    run_declaration: Path,
    task_brief: Path,
    treatment_scope: Path,
    destination: Path,
    receipt: Path,
    run_settings: Path | None = None,
    run_id: str | None = None,
) -> dict[str, object]:
    """Write a fresh workspace and its inventory; return the inventory.

    `run_id` instantiates the declaration (and every file under
    `run_settings`, copied to `run/`) for a run other than the one the
    committed declaration names — the smoke unit, for instance. Only the
    declared id is rewritten; every other byte is preserved.
    """
    payload = framework / PAYLOAD_RELATIVE
    for label, path in (
        ("toolkit payload AGENTS.md", payload / "AGENTS.md"),
        (
            "toolkit skill index",
            payload / ".agents" / "skills" / "siderius-toolkit" / "SKILL.md",
        ),
        ("run declaration", run_declaration),
        ("task brief", task_brief),
        ("treatment scope", treatment_scope),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"{label} is missing: {path}")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(
            f"workspace already exists; refusing to merge: {destination}"
        )
    if receipt.exists():
        raise FileExistsError(f"assembly receipt already exists: {receipt}")
    if receipt.resolve().parent == destination.resolve() or (
        destination.resolve() in receipt.resolve().parents
    ):
        raise ValueError("the assembly receipt must be written outside the workspace")

    declared = declared_run_id(run_declaration)
    run_id = run_id or declared
    if run_settings is not None and not run_settings.is_dir():
        raise FileNotFoundError(f"run settings directory is missing: {run_settings}")

    destination.mkdir(parents=True)
    files = _copy_tree(payload, destination)
    sources = {
        "run_declaration": run_declaration,
        "task_brief": task_brief,
        "treatment_scope": treatment_scope,
    }
    instantiated = {"run_declaration"}
    if run_settings is not None:
        for path in sorted(run_settings.iterdir()):
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"run settings must be regular files: {path}")
            label = f"run/{path.name}"
            sources[label] = path
            instantiated.add(label)
    for label, source in sources.items():
        relative = _DOCUMENTS.get(label, Path(label))
        target = destination / relative
        if target.exists():
            raise FileExistsError(
                f"payload already carries {relative}; refusing to overwrite"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        if label in instantiated:
            text = _instantiate(
                source.read_text(encoding="utf-8"), declared=declared, run_id=run_id
            )
            target.write_text(text, encoding="utf-8")
            if run_id == declared and _sha256(target) != _sha256(source):
                raise RuntimeError(f"bytes changed while copying {source}")
        else:
            shutil.copyfile(source, target)
            if _sha256(target) != _sha256(source):
                raise RuntimeError(f"bytes changed while copying {source}")
        files[str(relative)] = _sha256(target)

    inventory: dict[str, object] = {
        "version": "phyts-tess-orchestration-workspace-v1",
        "workspace": str(destination),
        "run_id": run_id,
        "declared_run_id": declared,
        "framework": str(framework),
        "framework_revision": _revision(framework),
        "payload": str(payload),
        "documents": {label: str(path) for label, path in sources.items()},
        "source_sha256": {label: _sha256(path) for label, path in sources.items()},
        "files": files,
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    return inventory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework", type=Path, required=True)
    parser.add_argument("--run-declaration", type=Path, required=True)
    parser.add_argument("--task-brief", type=Path, required=True)
    parser.add_argument("--treatment-scope", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument(
        "--receipt",
        type=Path,
        required=True,
        help="inventory path, outside the workspace",
    )
    parser.add_argument(
        "--run-settings",
        type=Path,
        default=None,
        help="directory of settings files copied to run/ (the declaration names them)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="instantiate the declaration for this run id instead of the one it names",
    )
    args = parser.parse_args(argv)
    inventory = assemble_workspace(
        framework=args.framework,
        run_declaration=args.run_declaration,
        task_brief=args.task_brief,
        treatment_scope=args.treatment_scope,
        destination=args.destination,
        receipt=args.receipt,
        run_settings=args.run_settings,
        run_id=args.run_id,
    )
    print(json.dumps({k: v for k, v in inventory.items() if k != "files"}, indent=2))
    print(f"{len(inventory['files'])} files written")  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
