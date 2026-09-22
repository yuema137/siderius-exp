"""Resolve fixed-workflow launch inputs without starting an experiment."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from experiments.shared.checksum_manifest import sha256_file
from experiments.shared.data_analysis_runtime import require_generated_analysis_runtime
from experiments.shared.fixed_workflow_config import render_siderius_args
from experiments.shared.framework_pin import (
    verify_framework_pin,
    verify_installed_framework,
)
from experiments.tidmad.information_treatments.prior_binding import (
    Prior,
    resolve_prior,
)
from experiments.tidmad.main_fixed_workflow.band_inputs import BANDS, verify_band_inputs
from experiments.tidmad.main_fixed_workflow.full_binding import (
    FullAnalysisInputs,
    verify_full_analysis_binding,
)


def _resolve_launch(
    repository_root: Path,
    siderius_checkout: Path,
    *,
    band: str,
    data_dir: Path,
    workspace: Path,
    run_name: str,
    require_fresh_workspace: bool = True,
    full_analysis: FullAnalysisInputs | None = None,
) -> dict[str, object]:
    """Build one reviewed command and its frozen-input receipt, fail closed."""

    root = repository_root.resolve()
    checkout = siderius_checkout.resolve()
    data = data_dir.resolve()
    run_workspace = workspace.resolve()
    if full_analysis is not None:
        full_analysis.require_external_to(root, checkout, data, run_workspace)
    if not run_name.strip():
        raise ValueError("run_name must be explicit and non-empty")
    if data.is_relative_to(root) or run_workspace.is_relative_to(root):
        raise ValueError(
            "data_dir and workspace must live outside the experiment checkout"
        )
    if data.is_relative_to(checkout) or run_workspace.is_relative_to(checkout):
        raise ValueError(
            "data_dir and workspace must live outside the framework checkout"
        )
    if run_workspace.is_relative_to(data) or data.is_relative_to(run_workspace):
        raise ValueError("data_dir and workspace must be separate directories")
    if (
        require_fresh_workspace
        and run_workspace.is_dir()
        and any(run_workspace.iterdir())
    ):
        raise ValueError("workspace must be fresh and empty")
    if run_workspace.exists() and not run_workspace.is_dir():
        raise ValueError("workspace must be a directory or not yet exist")

    revision = verify_framework_pin(root, checkout)
    verify_installed_framework(revision, root)
    launcher = checkout / "scripts/launch/run_chain.sh"
    if not launcher.is_file():
        raise ValueError(f"framework chain launcher is missing: {launcher}")
    data_receipt = verify_band_inputs(root, data, band)
    enabled = full_analysis is not None
    suffix = "full" if enabled else "no-prior"
    treatment = resolve_prior(root, Prior.ON if enabled else Prior.OFF)
    workflow = root / "experiments/tidmad/main_fixed_workflow/workflow.json"
    workflow_args = render_siderius_args(
        workflow, repository_root=root, siderius_checkout=checkout
    )
    analysis_receipt = None
    if full_analysis is not None:
        analysis_receipt = verify_full_analysis_binding(
            root,
            band=band,
            policy_path=full_analysis.policy_path,
            policy_sha256=full_analysis.policy_sha256,
            composition_path=full_analysis.composition_path,
        )
        # Full permits generated analysis. Refuse an incomplete deployment
        # before publishing either the initial or continuation clock. Keep
        # ephemeral host observations out of the immutable launch identity.
        require_generated_analysis_runtime(checkout)
        workflow_args[workflow_args.index("--task_composition") + 1] = analysis_receipt[
            "composition_path"
        ]
    literature = root / "tasks/tidmad/framework_configs/lit_review.yaml"
    if not literature.is_file():
        raise ValueError(f"literature-review config is missing: {literature}")
    command = [
        "bash",
        str(launcher),
        "--mode",
        "lilab",
        "--workspace",
        str(run_workspace),
        "--run_name",
        run_name,
        "--data_dir",
        str(data),
        "--data_scope",
        band,
        "--health_gate_files",
        band,
        "--ml_lit_review_config",
        str(literature),
        *workflow_args,
        *treatment.siderius_args(),
    ]
    receipt: dict[str, object] = {
        "version": f"tidmad-main-fixed-{suffix}-preflight-v1",
        "repository_revision": _git_revision(root),
        "task_package_tree": _git_revision(root, "HEAD:tasks/tidmad"),
        "siderius_revision": revision,
        "run_name": run_name,
        "workspace": str(run_workspace),
        "data_dir": str(data),
        "data": data_receipt,
        "workflow_sha256": sha256_file(workflow),
        "llm_config_sha256": sha256_file(
            root / "experiments/tidmad/main_fixed_workflow/iclr_official_v1.json"
        ),
        "literature_review_config_sha256": sha256_file(literature),
        "treatment": treatment.receipt(),
        "command": command,
    }
    if analysis_receipt is not None:
        receipt["analysis_binding"] = analysis_receipt
    return receipt


def resolve_no_prior_launch(
    repository_root: Path,
    siderius_checkout: Path,
    *,
    band: str,
    data_dir: Path,
    workspace: Path,
    run_name: str,
    require_fresh_workspace: bool = True,
) -> dict[str, object]:
    """Preserve the existing NoPrior command and receipt contract."""
    return _resolve_launch(
        repository_root,
        siderius_checkout,
        band=band,
        data_dir=data_dir,
        workspace=workspace,
        run_name=run_name,
        require_fresh_workspace=require_fresh_workspace,
    )


def resolve_full_launch(
    repository_root: Path,
    siderius_checkout: Path,
    *,
    band: str,
    data_dir: Path,
    workspace: Path,
    run_name: str,
    full_analysis: FullAnalysisInputs,
    require_fresh_workspace: bool = True,
) -> dict[str, object]:
    """Resolve Full with explicit analysis authority; never start its clock."""
    return _resolve_launch(
        repository_root,
        siderius_checkout,
        band=band,
        data_dir=data_dir,
        workspace=workspace,
        run_name=run_name,
        full_analysis=full_analysis,
        require_fresh_workspace=require_fresh_workspace,
    )


def _git_revision(root: Path, reference: str = "HEAD") -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", reference],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--siderius-checkout", type=Path, required=True)
    parser.add_argument("--band", choices=tuple(BANDS), required=True)
    parser.add_argument("--data_dir", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--run_name", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    receipt = resolve_no_prior_launch(
        root,
        args.siderius_checkout,
        band=args.band,
        data_dir=args.data_dir,
        workspace=args.workspace,
        run_name=args.run_name,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
