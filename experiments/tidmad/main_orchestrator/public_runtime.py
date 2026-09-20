"""Publish only research-side clients from an operator-owned experiment checkout."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

# Explicit files, never recursive copies of experiment/task/history directories.
# Scientific task imports resolve to the already-frozen public package below.
PUBLIC_FILES = (
    "SIDERIUS_REVISION",
    "pyproject.toml",
    "uv.lock",
    *(
        f"experiments/shared/{name}.py"
        for name in (
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
    ),
    *(
        f"experiments/tidmad/main_orchestrator/{name}.py"
        for name in (
            "baseline_evaluation",
            "baseline_receipt",
            "compact_training",
            "native_export",
            "validation_rows",
        )
    ),
    "experiments/tidmad/main_orchestrator/SUBMISSION.md",
    "experiments/shared/scripted_implementation.md",
    "experiments/shared/scripted_model_export.md",
    *(
        f"deployments/tidmad_coding_agent_baseline/tools/{name}.py"
        for name in (
            "archive_candidate",
            "io",
            "model",
            "segment_inference",
        )
    ),
)


def publish_public_runtime(root: Path, frozen_input: Path, output: Path) -> dict:
    """Create a new source distribution; no installation, launch or permission changes.

    The operator must protect the full checkout and prior qualification trees
    separately. This function does not hide another readable copy on the host.
    """
    root, frozen_input, output = (
        root.resolve(),
        frozen_input.resolve(),
        output.absolute(),
    )
    if output.exists() or output.is_symlink():
        raise ValueError("public runtime destination must be new")
    if output.resolve().is_relative_to(root) or output.resolve().is_relative_to(
        frozen_input
    ):
        raise ValueError("public runtime must be outside repository and frozen input")
    task_root = frozen_input / "tasks"
    if not task_root.is_dir() or (task_root / "tidmad/runtime/scoring.py").exists():
        raise ValueError("expected the frozen public task view without private scorer")
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    selected = {Path(name) for name in PUBLIC_FILES}
    for relative in tuple(selected):
        for parent in relative.parents:
            if parent != Path(".") and (root / parent / "__init__.py").is_file():
                selected.add(parent / "__init__.py")
    payloads = {}
    for relative in sorted(selected):
        source = root / relative
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError(f"public runtime source escapes checkout: {relative}")
        payloads[relative] = source.read_bytes()
    output.mkdir(parents=True, exist_ok=False)
    try:
        hashes = {}
        for relative, content in payloads.items():
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            hashes[str(relative)] = hashlib.sha256(content).hexdigest()
        # Preserve the exact existing public task files and module identities.
        (output / "tasks").symlink_to(task_root, target_is_directory=True)
        receipt = {
            "exp_revision": revision,
            "infra_revision": (root / "SIDERIUS_REVISION").read_text().strip(),
            "source_sha256": hashes,
            "frozen_public_tasks": str(task_root),
            "environment_installed": False,
            "host_access_qualified": False,
        }
        (output / "public-runtime.json").write_text(
            json.dumps(receipt, indent=2) + "\n"
        )
    except BaseException:
        shutil.rmtree(output)
        raise
    return receipt
