"""Emit an operator-only deployment bundle. Never start anything.

This is not a launcher. It starts no clock, calls no model, trains nothing
and scores nothing. It resolves what an external caller would need, verifies
that the result is publishable, and writes it to a directory outside both
repositories — then stops, leaving the launch decision where it belongs.

The bundle it writes:

```
composition.yaml       the public manifest, declaration without arithmetic
execution-policy.json  the bounds, derived from the fixed workflow
agent-models.json      LLM routing for the roles the caller may use
deployment.json        the receipt: revisions, digests, unresolved gates
operator-state/        generated-library isolation; NOT for the caller
```

What it deliberately does not resolve is anything about how the caller acts.
Selecting actions is what makes an orchestrator one.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

from experiments.phyts_tess.main_orchestrator.execution_policy import (
    resolve_execution_policy,
)
from experiments.phyts_tess.main_orchestrator.public_composition import (
    public_composition,
)
from experiments.phyts_tess.main_orchestrator.public_task_tree import (
    export_task_views,
    prune_bytecode,
)
from experiments.shared.checksum_manifest import sha256_file
from experiments.shared.framework_pin import (
    verify_framework_pin,
    verify_installed_framework,
)
from experiments.shared.information_treatment import (
    ModuleState,
    resolve_information_treatment,
)

__all__ = ["LAUNCH_BLOCKERS", "assert_view_is_publishable", "prepare"]

TREATMENT_RELATIVE_PATH = Path(
    "experiments/phyts_tess/information_treatments/main-fixed-no-prior.yaml"
)
AGENT_MODELS_RELATIVE_PATH = Path(
    "experiments/phyts_tess/main_fixed_workflow/agents.json"
)

#: Everything still standing between this bundle and a real run. Recorded so
#: the receipt cannot be mistaken for an authorization: `launch_ready` is
#: False and these say why.
LAUNCH_BLOCKERS = (
    (
        "Verify the native training binding against this task's [B, 1, 1024] "
        "shape; transfer from TIDMAD's geometry is unverified until a smoke "
        "run shows it."
    ),
    (
        "Install `tess-score` (machine/install_evaluator.sh) and bind the "
        "complete evaluator, TessCandidateEvaluator, in the process that runs "
        "the tuner; the published metric refuses to execute without one."
    ),
    (
        "Run the smoke in SMOKE.md under the operator-authorized budget "
        "(six hours, 8 GiB VRAM, matching nop_004) before any formal unit."
    ),
    (
        "Confirm the caller cannot read the evaluator view or the committed "
        "identity manifest through any path the deployment creates."
    ),
)


def assert_view_is_publishable(agent_view: Path) -> dict[str, object]:
    """Re-verify the answer separation on the bytes about to be published.

    Public because it is a contract, not a step: an operator can check a view
    before preparing anything, and the property deserves a boundary that can
    be tested without a whole preparation around it.

    The view was checked when it was built. It is checked again here because
    publication is the moment it leaves, and because the tool that built it
    and the bundle that ships it are separated by however long the operator
    took in between.
    """
    from tasks.phyts_tess.tools.build_views import assert_agent_view_is_answer_free

    if not agent_view.is_dir():
        raise ValueError(
            f"agent view not found at {agent_view}; build it with "
            "tasks/phyts_tess/tools/build_views.py"
        )
    try:
        assert_agent_view_is_answer_free(agent_view)
    except SystemExit as refusal:  # the tool is CLI-shaped; this is a contract
        # Re-raised, never swallowed. `SystemExit` derives from BaseException,
        # so a caller's `except Exception` would miss it and an embedding
        # process would simply exit — a refusal nobody can handle is nearly as
        # bad as no refusal.
        raise ValueError(str(refusal)) from refusal
    manifests = agent_view / "manifests"
    return {
        "root": str(agent_view),
        "train_manifest_sha256": sha256_file(manifests / "train.csv"),
        "predict_manifest_sha256": sha256_file(manifests / "predict.csv"),
        "evaluated_targets_present": False,
    }


def prepare(root: Path, checkout: Path, agent_view: Path, output: Path) -> dict:
    """Resolve, verify and write the bundle; return its receipt."""
    root, checkout = root.resolve(), checkout.resolve()
    agent_view, output = agent_view.resolve(), output.resolve()

    if output.exists():
        raise ValueError(
            "output must be a new directory; reusing one silently mixes two deployments"
        )
    if output.is_relative_to(root) or output.is_relative_to(checkout):
        raise ValueError("deployment artifacts must be outside both repositories")
    if agent_view.is_relative_to(output):
        raise ValueError("the agent view must not live inside the bundle")

    revision = verify_framework_pin(root, checkout)
    verify_installed_framework(revision, root)

    treatment = resolve_information_treatment(
        root / TREATMENT_RELATIVE_PATH,
        repository_root=root,
        adapter="siderius",
        required_modules=("literature_review", "data_analysis"),
    )
    if treatment.module_states["data_analysis"] is not ModuleState.DISABLED:
        raise ValueError(
            "this preparation is the no-prior condition; the selected treatment "
            "enables data analysis"
        )
    if treatment.declaration.advice.artifact is not None:
        raise ValueError("a no-prior bundle must carry no advice artifact")

    view = assert_view_is_publishable(agent_view)
    execution, workflow_digest = resolve_execution_policy(root, checkout)

    # Bind the generated library before any registry-bearing import, so a
    # preparation cannot inherit models from a user-level default the way an
    # unbound chain once did.
    from core.generated_library import bind_generated_library_to_workspace

    bind_generated_library_to_workspace(output / "operator-state")
    from workflows.task_composition import compose_run_task_bindings

    output.mkdir(parents=True, exist_ok=False)

    # Two views, named so the distinction cannot be missed: only `caller/`
    # may be handed over. `evaluator/` holds the scoring arithmetic and the
    # identity manifest, and lives here only because the single-host
    # deployment needs both halves produced together and from one revision.
    caller_tree = output / "caller"
    views = export_task_views(root, caller_tree, output / "evaluator")

    execution_path = output / "execution-policy.json"
    execution_path.write_text(
        execution.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    composition_path = output / "caller" / "composition.yaml"
    composition_path.write_text(
        yaml.safe_dump(
            public_composition(root, agent_view, caller_tree), sort_keys=False
        ),
        encoding="utf-8",
    )

    # Compose what was just written, not what was intended. The TESS pack's
    # own scoreability defect resolved cleanly per entry and failed only here.
    binding = compose_run_task_bindings(str(composition_path))
    if binding.secondary_metrics:
        raise ValueError("the published composition still carries secondary metrics")
    if binding.data_analysis is not None:
        raise ValueError("a no-prior bundle resolved an analysis binding")
    if type(binding.metric).__name__ != "CandidateEvaluationMetric":
        raise ValueError(
            "the published metric is not declaration-only; an external caller "
            f"would receive working arithmetic ({type(binding.metric).__name__})"
        )

    # Composing imported the copied modules, and CPython wrote bytecode
    # beside them. Those caches embed this machine's paths.
    views["bytecode_pruned"] = prune_bytecode(caller_tree)

    models = root / AGENT_MODELS_RELATIVE_PATH
    (output / "agent-models.json").write_bytes(models.read_bytes())

    receipt = {
        "schema_version": 1,
        "status": "operator_preparation_only",
        "launch_ready": False,
        "condition": "O-NoPrior",
        "deployment_shape": "single_host_two_process",
        "adversarially_isolated": False,
        "exp_revision": subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip(),
        "lock_sha256": sha256_file(root / "uv.lock"),
        "infra_revision": revision,
        "information_authority": treatment.receipt(),
        "literature_review_enabled": False,
        "data_analysis_enabled": False,
        "agent_view": view,
        "task_views": views,
        "handover": {
            "may_be_given_to_the_caller": ["caller/", "execution-policy.json"],
            "operator_only": ["evaluator/", "deployment.json", "agent-models.json"],
        },
        "composition_fingerprint": binding.semantic_fingerprint,
        "task_data_path_id": binding.task_data_path_id,
        "metric": {
            "id": binding.metric.spec.id,
            "direction": binding.metric.spec.direction,
            "implementation": "declaration_only",
        },
        "secondary_metrics_published": False,
        "agent_models_sha256": sha256_file(models),
        "fixed_workflow_sha256": workflow_digest,
        "execution_policy_sha256": sha256_file(execution_path),
        "execution_policy": execution.model_dump(mode="json"),
        "composition_sha256": sha256_file(composition_path),
        "agent_visible": False,
        "launch_blockers": list(LAUNCH_BLOCKERS),
    }
    (output / "deployment.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--siderius-checkout", type=Path, required=True)
    parser.add_argument(
        "--agent-view",
        type=Path,
        required=True,
        help="The agent/ directory written by tasks/phyts_tess/tools/build_views.py",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    receipt = prepare(
        Path(__file__).resolve().parents[3],
        args.siderius_checkout,
        args.agent_view,
        args.output,
    )
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
