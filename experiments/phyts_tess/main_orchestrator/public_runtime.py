"""Publish the research-side client modules an external caller runs.

The caller needs code, not just a manifest: the entry point it invokes, the
export and discovery helpers, and the validation client that talks to the
evaluator. This publishes exactly those into a new directory and nothing
else.

`PUBLIC_MODULES` is an **explicit list, never a recursive copy** of
`experiments/`. That directory holds other tasks' deployments and this
task's own operator-side code — `prepare.py`, `public_task_tree.py`, the
launcher policy verifier — none of which a caller may hold. A recursive copy
that picked up one more file than intended would be indistinguishable from
one that did not.

The shape is TIDMAD's `public_runtime.py`, and the shared list is copied
from it unchanged because those modules are task-generic. What differs is
the task's own additions and the refusal below, which checks for TESS's
private scorer rather than TIDMAD's.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

__all__ = ["PUBLIC_MODULES", "publish_public_runtime"]

#: Task-generic research-side machinery. Taken from TIDMAD's list, which is
#: the same set: none of these names a task.
_SHARED = (
    "builtin_objective_worker",
    "checksum_manifest",
    "epoch_model_worker",
    "inherited_validation_client",
    "native_loss_binding",
    "native_loss_discovery",
    "native_model_discovery",
    "native_model_export",
    "native_objective_metadata",
    "native_training_entry",
    "native_training_inputs",
    "native_training_metadata",
    "native_training_provenance",
    "objective_code_package",
    "objective_numerical_review",
    "objective_purpose_review",
    "objective_review",
    "objective_review_pipeline",
    "objective_source_check",
    "reviewed_objective_worker",
    "scripted_model_export",
    "scripted_implementation",
    "validation_client_factory",
    "validation_descriptor_transport",
    "validation_epoch_protocol",
    "validation_frames",
    "validation_module_protocol",
    "validation_module_worker",
    "validation_rng",
    "validation_snapshot",
    "validation_worker_config",
)

#: This task's own research-side additions. `validation_rows` is named by the
#: validation client through a `module:symbol` string, so it has to be here
#: or the client fails inside the first epoch. The three evaluator-client
#: modules are what the caller's process binds so the published metric can
#: execute; `tess_score` itself is the coordinator's and stays operator-only.
_TASK = (
    "validation_rows",
    "candidate_model",
    "tess_receipt",
    "tess_evaluation",
    "smoke_tuner",
)

PUBLIC_MODULES: tuple[str, ...] = (
    "SIDERIUS_REVISION",
    "pyproject.toml",
    "uv.lock",
    *(f"experiments/shared/{name}.py" for name in _SHARED),
    *(f"experiments/phyts_tess/main_orchestrator/{name}.py" for name in _TASK),
    "experiments/phyts_tess/main_orchestrator/SUBMISSION.md",
    "experiments/shared/scripted_implementation.md",
    "experiments/shared/scripted_model_export.md",
)

#: Never published. Operator-side code that lives in the same directory as
#: the task's research-side modules, which is exactly why the list above is
#: explicit.
OPERATOR_ONLY_MODULES = (
    "experiments/phyts_tess/main_orchestrator/prepare.py",
    "experiments/phyts_tess/main_orchestrator/public_task_tree.py",
    "experiments/phyts_tess/main_orchestrator/verify_launcher_policy.py",
    "experiments/phyts_tess/main_orchestrator/native_handler.py",
    "experiments/phyts_tess/main_orchestrator/validation_scope.py",
    "experiments/phyts_tess/main_orchestrator/tess_score.py",
    "experiments/phyts_tess/main_orchestrator/verify_evaluator_policy.py",
    "experiments/phyts_tess/main_orchestrator/draft_launcher_policy.py",
    "experiments/phyts_tess/main_orchestrator/stage_policy.py",
    "experiments/phyts_tess/main_orchestrator/assemble_workspace.py",
    "experiments/phyts_tess/main_orchestrator/machine/probe_namespace.py",
)


def publish_public_runtime(root: Path, caller_tree: Path, output: Path) -> dict:
    """Write a new source distribution; install nothing, launch nothing.

    `caller_tree` is the bundle's `caller/` view, which the published runtime
    links to so the task package the caller imports is the one already
    checked to be answer-free.
    """
    root, caller_tree = root.resolve(), caller_tree.resolve()
    output = output.absolute()

    if output.exists() or output.is_symlink():
        raise ValueError("public runtime destination must be new")
    if output.resolve().is_relative_to(root) or output.resolve().is_relative_to(
        caller_tree
    ):
        raise ValueError("public runtime must be outside the repository and the bundle")

    task_root = caller_tree / "tasks"
    if not task_root.is_dir():
        raise ValueError(f"expected the bundle's public task view at {task_root}")
    if (task_root / "phyts_tess/runtime/scoring.py").exists():
        raise ValueError(
            "the supplied task view still carries the private scorer; publish "
            "from the caller view, not the evaluator one"
        )

    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()

    selected = {Path(name) for name in PUBLIC_MODULES}
    for relative in tuple(selected):
        for parent in relative.parents:
            if parent != Path(".") and (root / parent / "__init__.py").is_file():
                selected.add(parent / "__init__.py")

    payloads: dict[Path, bytes] = {}
    for relative in sorted(selected):
        source = root / relative
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError(f"public runtime source escapes the checkout: {relative}")
        payloads[relative] = source.read_bytes()

    output.mkdir(parents=True, exist_ok=False)
    try:
        digests: dict[str, str] = {}
        for relative, content in payloads.items():
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            digests[str(relative)] = hashlib.sha256(content).hexdigest()

        # Linked, not copied: the caller imports the same task package the
        # bundle already proved answer-free, rather than a second copy that
        # could drift from it.
        (output / "tasks").symlink_to(task_root, target_is_directory=True)

        for operator_only in OPERATOR_ONLY_MODULES:
            if (output / operator_only).exists():
                raise ValueError(f"{operator_only} reached the published runtime")

        receipt = {
            "exp_revision": revision,
            "infra_revision": (root / "SIDERIUS_REVISION")
            .read_text(encoding="utf-8")
            .strip(),
            "source_sha256": digests,
            "public_tasks": str(task_root),
            "environment_installed": False,
            "host_access_qualified": False,
        }
        (output / "public-runtime.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
    except BaseException:
        shutil.rmtree(output, ignore_errors=True)
        raise
    return receipt
