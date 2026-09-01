"""Task-owned DAVIS future-frame prediction contract checks."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path


EXP_ROOT = Path(__file__).resolve().parents[3]
PACK = EXP_ROOT / "tasks" / "davis_future_prediction"
COMPOSITION = PACK / "compositions" / "bounded_qualification.yaml"
MANIFESTS = PACK / "data" / "manifests"
EXPERIMENT = (
    EXP_ROOT / "experiments" / "davis_future_prediction" / "two_iteration_qualification"
)
LAUNCHER = EXPERIMENT / "launch.sh"
EXPECTED_FRAMEWORK_REVISION = (
    (EXP_ROOT / "SIDERIUS_REVISION").read_text(encoding="utf-8").strip()
)

COMPOSE_CHILD = textwrap.dedent(
    """
    import json
    import sys
    from pathlib import Path

    checkout = Path(sys.argv[1]).resolve()
    manifest = Path(sys.argv[2]).resolve()
    pack = manifest.parent.parent
    sys.path.insert(0, str(checkout))

    from workflows import task_composition as composition_module
    from workflows.task_composition import compose_run_task_bindings

    source = Path(composition_module.__file__).resolve()
    if not source.is_relative_to(checkout):
        raise RuntimeError(
            f"source-authority violation: imported {source}, expected {checkout}"
        )

    composition = compose_run_task_bindings(str(manifest))
    sources = list(composition.provenance.source_paths.values())
    plugins = [item.absolute_path for item in composition.provenance.plugins]
    print(
        json.dumps(
            {
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
                "partition_count": composition.dataset_profile.partition_count,
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_composition_resolves_only_task_owned_science() -> None:
    """The external package must own its task semantics and plugin sources."""
    checkout = _siderius_checkout()
    completed = subprocess.run(
        [sys.executable, "-c", COMPOSE_CHILD, str(checkout), str(COMPOSITION)],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout.splitlines()[-1])
    assert receipt == {
        "all_sources_task_owned": True,
        "health_binding": str((PACK / "declared" / "task_health.yaml").resolve()),
        "objective": ["custom", "davis_exact_l1"],
        "partition_count": 60,
        "primary": ["mse", "lower"],
        "secondaries": [["psnr", "higher"], ["mae", "lower"]],
        "task_data_path_id": "davis_future_prediction",
        "task_type": "regression",
    }


def test_every_committed_manifest_matches_its_provenance_pin() -> None:
    """Every task-owned sequence or clip manifest remains pinned."""
    pins: dict[str, str] = {}
    for line in (MANIFESTS / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        pins[name.strip()] = digest

    present = {path.name for path in MANIFESTS.glob("*.csv")}
    assert set(pins) == present
    for name, expected in pins.items():
        assert _sha256(MANIFESTS / name) == expected


def test_sequence_roles_are_disjoint() -> None:
    """No sequence may cross the training, validation, and final roles."""
    rows = (MANIFESTS / "sequences.csv").read_text(encoding="utf-8").splitlines()[1:]
    role_ids: dict[str, set[str]] = {
        "train": set(),
        "validation": set(),
        "final": set(),
    }
    for row in rows:
        sequence, role = row.split(",")
        role_ids[role].add(sequence)

    assert role_ids["train"].isdisjoint(role_ids["validation"])
    assert role_ids["train"].isdisjoint(role_ids["final"])
    assert role_ids["validation"].isdisjoint(role_ids["final"])


def test_task_package_contains_no_experiment_launcher() -> None:
    """Static task ownership must not absorb workflow treatment values."""
    assert not (PACK / "quickstart.sh").exists()
    assert not (PACK / "workflows").exists()
    assert LAUNCHER.is_file()


def test_experiment_dry_run_preserves_the_qualification_treatment(
    tmp_path: Path,
) -> None:
    """The experiment must select the exact task, workflow, and parameter values."""
    checkout = _siderius_checkout()
    workspace = tmp_path / "workspace"
    data_dir = tmp_path / "davis"
    (data_dir / "DAVIS" / "JPEGImages" / "480p").mkdir(parents=True)
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(Path(sys.executable).resolve().parents[1])

    completed = subprocess.run(
        [
            "bash",
            str(LAUNCHER),
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
        "--run_name": "davis_qualification",
        "--max_rounds": "2",
        "--max_epochs": "1",
        "--trial_portion": "1.0",
        "--train_portion": "1.0",
        "--formal_portion": "1.0",
        "--formal_train_portion": "1.0",
        "--formal_eval_portion": "1.0",
        "--validation_max_samples": "15",
        "--min_formal_batch_size": "1",
        "--allowed_output_types": "regressor",
        "--trial_vram_budget_gb": "10",
        "--formal_vram_budget_gb": "16",
        "--vram_preflight_host_memory_limit_gb": "32",
    }
    for index, command in enumerate(commands, start=1):
        assert command[command.index("--start_iteration") + 1] == str(index)
        assert command[command.index("--task_composition") + 1] == str(COMPOSITION)
        for flag, expected in expected_values.items():
            assert command[command.index(flag) + 1] == expected
