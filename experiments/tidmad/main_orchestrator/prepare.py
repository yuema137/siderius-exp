"""Prepare operator-only deployment candidates; never start an experiment."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

from experiments.shared.checksum_manifest import sha256_file
from experiments.shared.framework_pin import (
    verify_framework_pin,
    verify_installed_framework,
)
from experiments.tidmad.main_fixed_workflow.band_inputs import BANDS
from experiments.tidmad.main_orchestrator.execution_policy import (
    resolve_execution_policy,
)
from experiments.tidmad.main_orchestrator.policy import (
    Prior,
    candidate_analysis_policy,
    composition_overlay,
    materialize_controller_strategy,
    resolve_prior,
)

COMMON_LAUNCH_BLOCKERS = (
    "Bind the unchanged frozen public task view and verify its content identity.",
    "Reuse baseline account/data/scoring permissions; protect installed infra and frozen task.",
    "Reuse agreed baseline outer Codex settings, data identity, clock and restart policy.",
    "Verify full-band candidate replay and the deployed combination before formal launch.",
)
FULL_LAUNCH_BLOCKERS = (
    "Verify the deployed frozen Full analysis policy and model-advice hashes.",
    "Expose the certified controller strategy only to the outer controller and link it from SIDERIUS-RUN.md.",
)


def deployment_status(
    prior: Prior, *, strategy_only: bool = False
) -> tuple[str, list[str]]:
    """Return treatment status and the remaining machine-owned launch gates."""
    prior = Prior(prior)
    blockers = list(COMMON_LAUNCH_BLOCKERS)
    if strategy_only:
        if prior is not Prior.OFF:
            raise ValueError(
                "strategy-only requires prior off: Data Analysis and model advice disabled"
            )
        blockers.extend(
            (
                "Verify Data Analysis denial and absence of analysis inputs, findings and model advice from the research view.",
                "Bind the protected V3 prompt supplement at every outer invocation and qualify context recovery.",
            )
        )
        return "strategy_only_v3", blockers
    if prior is Prior.ON:
        blockers.extend(FULL_LAUNCH_BLOCKERS)
        return "frozen_full_v8", blockers
    return "disabled", blockers


def prepare(
    root: Path,
    checkout: Path,
    output: Path,
    *,
    prior: Prior,
    band: str,
    strategy_only: bool = False,
) -> dict:
    """Certify pins and native binding, recording unresolved launch requirements."""
    prior = Prior(prior)
    analysis_policy_status, blockers = deployment_status(
        prior, strategy_only=strategy_only
    )
    root, checkout, output = root.resolve(), checkout.resolve(), output.resolve()
    if band not in BANDS:
        raise ValueError(f"unsupported band: {band}")
    if output.exists():
        raise ValueError(
            "output must be a new directory; never reuse another treatment"
        )
    if output.is_relative_to(root) or output.is_relative_to(checkout):
        raise ValueError("deployment artifacts must be outside protected repositories")
    revision = verify_framework_pin(root, checkout)
    verify_installed_framework(revision, root)
    treatment = resolve_prior(root, prior)
    execution, workflow_digest = resolve_execution_policy(root, checkout)
    # Bind before registry-bearing native imports; preparation is operator-owned.
    from core.generated_library import bind_generated_library_to_workspace

    bind_generated_library_to_workspace(output / "operator-state")
    from workflows.run_one_iteration import load_advice_artifact, render_advice_value
    from workflows.task_composition import compose_run_task_bindings

    output.mkdir(parents=True, exist_ok=False)
    execution_path = output / "execution-policy.json"
    execution_path.write_text(execution.model_dump_json(indent=2) + "\n")
    analysis_path = None
    if prior is Prior.ON:
        analysis_path = output / "analysis-policy.yaml"
        policy = candidate_analysis_policy(root, band)
        analysis_path.write_text(
            yaml.safe_dump(policy.model_dump(mode="json"), sort_keys=False)
        )
    composition = output / "composition.yaml"
    composition.write_text(
        yaml.safe_dump(composition_overlay(root, analysis_path), sort_keys=False)
    )
    binding = compose_run_task_bindings(str(composition))
    if (binding.data_analysis is not None) != (prior is Prior.ON):
        raise ValueError("native analysis binding disagrees with the prior switch")
    advice_routing = {}
    controller_strategy = None
    if prior is Prior.ON:
        assert treatment.advice_path is not None
        advice = load_advice_artifact(
            str(treatment.advice_path),
            declared_sha256=treatment.declaration.advice.sha256,
        )
        (output / "advice.json").write_bytes(treatment.advice_path.read_bytes())
        advice_routing = {
            key: render_advice_value(value)
            for key, value in advice.content.items()
            if not key.startswith("_")
        }
        controller_strategy = materialize_controller_strategy(root, output)
    if strategy_only:
        controller_strategy = materialize_controller_strategy(
            root, output, strategy_only=True
        )
        from deployments.tidmad_coding_agent_baseline.tools.prompt_supplement import (
            PromptSupplement,
        )

        supplement = PromptSupplement(
            artifact=controller_strategy.artifact,
            sha256=controller_strategy.sha256,
        )
        (output / "prompt-supplement.json").write_text(supplement.to_json())
    llm = root / "experiments/tidmad/main_fixed_workflow/iclr_official_v1.json"
    (output / "agent-models.json").write_bytes(llm.read_bytes())
    receipt = {
        "schema_version": 1,
        "status": "operator_preparation_only",
        "launch_ready": False,
        "prior": prior.value,
        "condition": "O-StrategyOnly"
        if strategy_only
        else ("O-Full" if prior is Prior.ON else "O-NoPrior"),
        "band": band,
        "data_scope": {"file_indices": list(BANDS[band])},
        "exp_revision": subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip(),
        "lock_sha256": sha256_file(root / "uv.lock"),
        "infra_revision": revision,
        "wrapper_revision": revision,
        "fixed_information_authority": treatment.receipt(),
        "literature_review_enabled": True,
        "data_analysis_enabled": prior is Prior.ON,
        "native_analysis_binding_resolved": binding.data_analysis is not None,
        "analysis_policy_status": analysis_policy_status,
        "analysis_policy_sha256": sha256_file(analysis_path) if analysis_path else None,
        "advice_sha256": treatment.declaration.advice.sha256,
        "advice_by_recipient": advice_routing,
        "controller_strategy_advice": (
            controller_strategy.receipt() if controller_strategy else None
        ),
        "agent_models_sha256": sha256_file(llm),
        "fixed_workflow_sha256": workflow_digest,
        "execution_policy_sha256": sha256_file(execution_path),
        "execution_policy": execution.model_dump(mode="json"),
        "execution_policy_enforcement": "pending_deployed_native_route",
        "composition_fingerprint": binding.semantic_fingerprint,
        "operator_composition": str(composition),
        "agent_visible": False,
        "launch_blockers": blockers,
    }
    if strategy_only:
        receipt["prompt_supplement"] = "prompt-supplement.json"
        receipt["model_advice_enabled"] = False
    (output / "deployment.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    treatment = parser.add_mutually_exclusive_group(required=True)
    treatment.add_argument("--prior", type=Prior, choices=list(Prior))
    treatment.add_argument("--strategy-only", action="store_true")
    parser.add_argument("--band", choices=list(BANDS), required=True)
    parser.add_argument("--siderius-checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = prepare(
        Path(__file__).resolve().parents[3],
        args.siderius_checkout,
        args.output,
        prior=args.prior or Prior.OFF,
        band=args.band,
        strategy_only=args.strategy_only,
    )
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
