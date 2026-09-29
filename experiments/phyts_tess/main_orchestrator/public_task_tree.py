"""Export the task package into a public view and an evaluator-only view.

Producing the bundle is what exposed the need for this. The published
manifest resolves every reference to an absolute path, and those paths
pointed **into siderius-exp** — so a caller could not compose the manifest
without read access to the repository, and that repository carries
`runtime/scoring.py` and the identity manifest with its validation targets.
A bundle that requires the repository is not a bundle.

The mechanism is TIDMAD's, deliberately
(`deployments/tidmad_coding_agent_baseline/tools/build_bundle.py`): take the
**git-tracked** task files, refuse a tree with uncommitted changes, copy
everything into the evaluator view, and copy into the public view only what
the classifier does not withhold. One authority, exported twice.

Following it rather than inventing an allowlist matters for a reason beyond
consistency: the single-host deployment needs the evaluator view as much as
the public one, and a mechanism that produced only the public half would
leave the other side to be assembled by hand.

**What TIDMAD withholds, and what that settles.** Its evaluator-only set is
the scoring implementation, the truth-bearing reference data and the
ground-truth tools — and *not* `runtime/scoreability.py`. That is an
independent precedent for the call recorded in EXECUTION_BOUNDARY.md: the
format validator crosses, the arithmetic does not.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

__all__ = [
    "EVALUATOR_ONLY_FILES",
    "TASK_PACKAGE",
    "export_task_views",
    "prune_bytecode",
    "tracked_task_files",
]

TASK_PACKAGE = Path("tasks/phyts_tess")

#: Bytes that implement private scoring or carry the answers. Everything else
#: tracked under the task package is public.
EVALUATOR_ONLY_FILES = frozenset(
    {
        # The arithmetic that turns predictions into a score.
        TASK_PACKAGE / "runtime" / "scoring.py",
        # Validation targets. The public view's data path reads the
        # answer-free agent view instead.
        TASK_PACKAGE / "data" / "manifests" / "rotation_identity.csv",
        # The public composition drops these observational metrics; shipping
        # their declarations would only invite a caller to compute them, and
        # the implementation it would need is withheld anyway.
        TASK_PACKAGE / "declared" / "metric_rmse.json",
        TASK_PACKAGE / "declared" / "metric_mae.json",
    }
)


def tracked_task_files(repo: Path) -> list[Path]:
    """Every committed file under the task package, or refuse.

    A snapshot taken from a tree with uncommitted changes cannot be
    reproduced from its recorded revision, so it is refused rather than
    taken.
    """
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", str(TASK_PACKAGE)],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status.strip():
        raise ValueError(
            f"{TASK_PACKAGE} has uncommitted changes; refusing a snapshot that "
            "its recorded revision would not reproduce"
        )
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--", str(TASK_PACKAGE)],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout
    return [repo / item.decode() for item in listed.split(b"\0") if item]


def _copy(source: Path, repo: Path, destination: Path) -> Path:
    target = destination / source.relative_to(repo)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def prune_bytecode(root: Path) -> list[str]:
    """Remove `__pycache__` written by importing the exported modules.

    Composing the published manifest imports the copied modules, and CPython
    writes bytecode beside them. Those caches embed the **source path on the
    machine that produced them**, so shipping them would leak an operator's
    directory layout into a bundle meant for someone else.
    """
    removed: list[str] = []
    for cache in sorted(root.rglob("__pycache__")):
        if cache.is_dir():
            removed.append(str(cache.relative_to(root)))
            shutil.rmtree(cache)
    return removed


def _tree_identity(root: Path) -> str:
    """Identify a materialized tree without depending on host paths.

    Digests relative paths and content, so the same export from two
    checkouts at two absolute locations has one identity. Bytecode caches
    are excluded: they are a side effect of reading the tree, not part of
    what was published.
    """
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def export_task_views(repo: Path, public: Path, evaluator: Path) -> dict[str, object]:
    """Write both views and report what each contains.

    The public view additionally receives the orchestrator's own
    `public_data_path.py`, published *inside* the package it subclasses so
    its absolute import resolves with only the bundle on the path.
    """
    repo = repo.resolve()
    for destination in (public, evaluator):
        if destination.exists():
            raise ValueError(f"refusing to write into an existing view: {destination}")

    published: list[str] = []
    withheld: list[str] = []
    for source in tracked_task_files(repo):
        relative = source.relative_to(repo)
        _copy(source, repo, evaluator)
        if relative in EVALUATOR_ONLY_FILES:
            withheld.append(str(relative))
        else:
            _copy(source, repo, public)
            published.append(str(relative))

    if not withheld:
        raise ValueError(
            "nothing was withheld; the classifier matched no tracked file, which "
            "means the public view is the whole task package"
        )

    data_path = Path(__file__).with_name("public_data_path.py")
    target = public / TASK_PACKAGE / "runtime" / "public_data_path.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(data_path, target)
    published.append(str(target.relative_to(public)))

    # Asserted on what was written, not on what was intended.
    for relative in EVALUATOR_ONLY_FILES:
        if (public / relative).exists():
            raise ValueError(f"{relative} reached the public view; it is withheld")

    return {
        "published_files": sorted(published),
        "withheld_files": sorted(withheld),
        "public_tree_sha256": _tree_identity(public),
        "evaluator_tree_sha256": _tree_identity(evaluator),
    }
