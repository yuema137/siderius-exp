"""Cold-process startup witnesses for every real external task composition.

These tests stop before any LLM or GPU work. They exercise the production
composition, formal-launch policy, task-owned Health plugin binding, complete
DataScope resolution, and run-invariant materialization against one explicitly
selected SIDERIUS checkout.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


EXP_ROOT = Path(__file__).resolve().parents[1]
TASK_MANIFESTS = {
    "tidmad": EXP_ROOT / "tasks/tidmad/compositions/bounded_qualification.yaml",
    "oxford_iiit_pet": EXP_ROOT
    / "tasks/oxford_iiit_pet/compositions/bounded_qualification.yaml",
    "davis_future_prediction": EXP_ROOT
    / "tasks/davis_future_prediction/compositions/bounded_qualification.yaml",
    "cancer_gene_identification": (
        EXP_ROOT / "tasks/cancer_gene_identification/compositions/two_network.yaml"
    ),
}
EXPECTED_OBJECTIVES = {
    "tidmad": None,
    "oxford_iiit_pet": ("ce", None),
    "davis_future_prediction": ("custom", "davis_exact_l1"),
    "cancer_gene_identification": ("custom", "cancer_gene_masked_bce"),
}
EXPECTED_HEALTH_GATES = {
    "tidmad": {
        "amplitude_collapse_blocking",
        "output_diversity_blocking",
        "output_std_blocking",
    },
    "oxford_iiit_pet": {
        "pets_distinct_symbols_blocking",
        "pets_dominant_fraction_blocking",
    },
    "davis_future_prediction": {"davis_dispersion_blocking"},
    "cancer_gene_identification": set(),
}

CHILD = textwrap.dedent(
    """
    import json
    import os
    import sys
    from pathlib import Path

    checkout = Path(sys.argv[1]).resolve()
    manifest = Path(sys.argv[2]).resolve()
    workspace = Path(sys.argv[3]).resolve()
    sys.path.insert(0, str(checkout))
    os.chdir(checkout)

    from core.run_invariants import RunHealthMaterialization, build_run_invariants
    from execute_tools.dataset_config import DataScope
    from execute_tools.health_checks.candidate_eligibility import resolve_run_scientific_gate_ids
    from execute_tools.health_checks.launch_policy import validate_formal_launch
    from workflows import task_composition as composition_module
    from workflows.task_composition import compose_run_task_bindings

    source = Path(composition_module.__file__).resolve()
    if not source.is_relative_to(checkout):
        raise RuntimeError(
            f"source-authority violation: imported {source}, expected checkout {checkout}"
        )

    composition = compose_run_task_bindings(str(manifest))
    partition_count = composition.dataset_profile.partition_count
    resolved_scope = DataScope.default().resolve(partition_count)

    validate_formal_launch(
        healthgate_mode="blocking",
        result_authority="scientific",
        health_checks_config=None,
        gates_enabled=True,
        skip_formal_min_delta=-1.0,
        bypass_formal_time_budget_min_delta=0.0,
        task_health_binding=composition.task_health_binding,
    )
    invariants, effective_path = build_run_invariants(
        resolved_data_scope=resolved_scope,
        health_gate_enabled=True,
        health_gate_files=None,
        health_checks_config=None,
        workspace=str(workspace),
        include_runtime_identities=False,
        health_materialization=RunHealthMaterialization(
            task_health_binding=composition.task_health_binding,
            dataset_partition_count=partition_count,
        ),
        task_composition_fingerprint=composition.semantic_fingerprint,
    )
    print(
        json.dumps(
            {
                "partition_count": partition_count,
                "resolved_scope_count": len(invariants.resolved_data_scope),
                "effective_health_config": effective_path,
                "objective_loss_type": (
                    composition.objective.loss_type
                    if composition.objective is not None
                    else None
                ),
                "objective_loss_name": (
                    composition.objective.loss_name
                    if composition.objective is not None
                    else None
                ),
                "health_gate_ids": sorted(
                    resolve_run_scientific_gate_ids(composition.task_health_binding)
                    or []
                ),
                "source_checkout": str(checkout),
            },
            sort_keys=True,
        )
    )
    """
)


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        pytest.fail(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    checkout = Path(configured).resolve()
    if not (checkout / "core/run_invariants.py").is_file():
        pytest.fail(f"SIDERIUS_CHECKOUT is not a SIDERIUS checkout: {checkout}")
    return checkout


@pytest.mark.parametrize("task_id", TASK_MANIFESTS)
def test_real_task_cold_start_reaches_the_llm_gpu_boundary(
    task_id: str, tmp_path: Path
) -> None:
    """Fail when startup reselects legacy Health or dataset authority.

    Removing this test would leave two observed failures uncovered: formal
    launch binding an empty legacy plugin set before a task-owned plugin, and
    full-scope validation comparing an external task with the legacy task's
    partition count.
    """
    checkout = _siderius_checkout()
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            CHILD,
            str(checkout),
            str(TASK_MANIFESTS[task_id]),
            str(tmp_path / task_id),
        ],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout.splitlines()[-1])
    assert receipt["partition_count"] == receipt["resolved_scope_count"]
    assert Path(receipt["effective_health_config"]).is_file()
    assert Path(receipt["source_checkout"]) == checkout
    expected_objective = EXPECTED_OBJECTIVES[task_id]
    actual_objective = (
        receipt["objective_loss_type"],
        receipt["objective_loss_name"],
    )
    if expected_objective is None:
        assert actual_objective == (None, None)
    else:
        assert actual_objective == expected_objective
    assert set(receipt["health_gate_ids"]) == EXPECTED_HEALTH_GATES[task_id]
