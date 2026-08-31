"""Task-owned NatureBench cancer-gene contract checks."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


EXP_ROOT = Path(__file__).resolve().parents[3]
PACK = EXP_ROOT / "tasks" / "cancer_gene_identification"
COMPOSITIONS = {
    "two_network_qualification": PACK / "compositions" / "two_network.yaml",
    "eight_network_comparison": PACK / "compositions" / "eight_network.yaml",
}
EXPECTED_NETWORKS = {
    "two_network_qualification": ["cpdb", "ltg"],
    "eight_network_comparison": [
        "cpdb",
        "stringdb",
        "pcnet",
        "iref_v15",
        "iref_v9",
        "multinet",
        "mtg",
        "ltg",
    ],
}
LAUNCHER = EXP_ROOT / "experiments" / "cancer_gene_identification" / "launch.sh"
EXPECTED_FRAMEWORK_REVISION = "97523a99df436179c673db0abcfaa0ce8d8042e4"

COMPOSE_CHILD = textwrap.dedent(
    """
    import json
    import sys
    from pathlib import Path

    checkout = Path(sys.argv[1]).resolve()
    manifest = Path(sys.argv[2]).resolve()
    pack = manifest.parent.parent
    sys.path.insert(0, str(checkout))

    from execute_tools.task_data_path import (
        ScopeBuildRequest,
        resolve_task_scope_capability,
    )
    from workflows import task_composition as composition_module
    from workflows.task_composition import compose_run_task_bindings

    source = Path(composition_module.__file__).resolve()
    if not source.is_relative_to(checkout):
        raise RuntimeError(
            f"source-authority violation: imported {source}, expected {checkout}"
        )

    composition = compose_run_task_bindings(str(manifest))
    scope = resolve_task_scope_capability(
        composition.task_data_path
    ).build_training_scope(
        ScopeBuildRequest(round_kind="formal", selection_strategy="snapshot", portion=1.0)
    )
    sources = list(composition.provenance.source_paths.values())
    plugins = [item.absolute_path for item in composition.provenance.plugins]
    print(
        json.dumps(
            {
                "instances": list(scope.instances),
                "task_data_path_id": composition.task_data_path.task_data_path_id,
                "primary": [
                    composition.metric.spec.id,
                    composition.metric.spec.direction,
                ],
                "secondaries": [
                    [metric.spec.id, metric.spec.direction]
                    for metric in composition.secondary_metrics
                ],
                "objective": [
                    composition.objective.loss_type,
                    composition.objective.loss_name,
                ],
                "task_type": composition.forward_contract.task_type,
                "health_binding": composition.task_health_binding,
                "all_sources_task_owned": all(
                    Path(path).resolve().is_relative_to(pack)
                    for path in [*sources, *plugins]
                ),
            },
            sort_keys=True,
        )
    )
    """
)


def _siderius_checkout() -> Path:
    configured = os.environ.get("SIDERIUS_CHECKOUT")
    if not configured:
        raise AssertionError(
            "SIDERIUS_CHECKOUT must name the exact SIDERIUS checkout under test"
        )
    checkout = Path(configured).resolve()
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    assert revision == EXPECTED_FRAMEWORK_REVISION
    return checkout


@pytest.mark.parametrize("experiment", COMPOSITIONS)
def test_compositions_share_science_and_vary_only_task_scope(experiment: str) -> None:
    """Both reusable scopes must bind the same task-owned scientific contract."""
    checkout = _siderius_checkout()
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            COMPOSE_CHILD,
            str(checkout),
            str(COMPOSITIONS[experiment]),
        ],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout.splitlines()[-1])
    assert receipt == {
        "all_sources_task_owned": True,
        "health_binding": "explicit_none",
        "instances": EXPECTED_NETWORKS[experiment],
        "objective": ["custom", "cancer_gene_masked_bce"],
        "primary": ["mean_auprc", "higher"],
        "secondaries": [["mean_auroc", "higher"]],
        "task_data_path_id": "naturebench_cancer_gene",
        "task_type": "regression",
    }


def test_task_package_contains_no_experiment_or_workflow_launcher() -> None:
    """Static task ownership must not absorb workflow or experiment identity."""
    assert not (PACK / "quickstart.sh").exists()
    assert not (PACK / "workflows").exists()
    assert LAUNCHER.is_file()


@pytest.mark.parametrize("experiment", COMPOSITIONS)
def test_experiment_dry_run_preserves_the_trial_formal_treatment(
    experiment: str, tmp_path: Path
) -> None:
    """Each experiment selects one task scope over the same workflow treatment."""
    checkout = _siderius_checkout()
    workspace = tmp_path / experiment
    data_dir = tmp_path / "data"
    for network in EXPECTED_NETWORKS[experiment]:
        network_dir = data_dir / network
        network_dir.mkdir(parents=True, exist_ok=True)
        (network_dir / "data.h5").touch()
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(Path(sys.executable).resolve().parents[1])

    completed = subprocess.run(
        [
            "bash",
            str(LAUNCHER),
            "--experiment",
            experiment,
            "--siderius-checkout",
            str(checkout),
            "--workspace",
            str(workspace),
            "--data_dir",
            str(data_dir),
            "--dry-run",
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    commands = [
        shlex.split(line.strip())
        for line in completed.stdout.splitlines()
        if "run_one_iteration.py" in line
    ]
    assert len(commands) == 2
    expected_values = {
        "--run_name": "cancer_gene_quickstart",
        "--max_rounds": "2",
        "--max_epochs": "1",
        "--trial_portion": "0.25",
        "--eval_portion": "0.25",
        "--formal_portion": "1.0",
        "--formal_train_portion": "0.25",
        "--formal_eval_portion": "0.25",
        "--min_formal_batch_size": "1",
        "--allowed_output_types": "regressor",
        "--trial_vram_budget_gb": "10",
        "--formal_vram_budget_gb": "16",
    }
    for index, command in enumerate(commands, start=1):
        assert command[command.index("--start_iteration") + 1] == str(index)
        assert command[command.index("--task_composition") + 1] == str(
            COMPOSITIONS[experiment]
        )
        assert "--no-runtime_watchdog" in command
        for flag, expected in expected_values.items():
            assert command[command.index(flag) + 1] == expected
