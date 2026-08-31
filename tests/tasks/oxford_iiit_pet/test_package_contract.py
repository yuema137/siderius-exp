"""Task-owned contract checks for the Oxford-IIIT Pet package."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml


EXP_ROOT = Path(__file__).resolve().parents[3]
PACK = EXP_ROOT / "tasks" / "oxford_iiit_pet"
COMPOSITION = PACK / "compositions" / "bounded_qualification.yaml"
MANIFESTS = PACK / "data" / "manifests"
EXPERIMENT = (
    EXP_ROOT / "experiments" / "oxford_iiit_pet" / "two_iteration_qualification"
)
LAUNCHER = EXPERIMENT / "launch.sh"
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

    from workflows import task_composition as composition_module
    from workflows.task_composition import compose_run_task_bindings

    source = Path(composition_module.__file__).resolve()
    if not source.is_relative_to(checkout):
        raise RuntimeError(
            f"source-authority violation: imported {source}, expected {checkout}"
        )

    composition = compose_run_task_bindings(str(manifest))
    source_paths = list(composition.provenance.source_paths.values())
    plugin_paths = [item.absolute_path for item in composition.provenance.plugins]
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
                    composition.objective.reduction,
                ],
                "task_type": composition.forward_contract.task_type,
                "num_classes": composition.forward_contract.num_classes,
                "partition_count": composition.dataset_profile.partition_count,
                "health_binding": composition.task_health_binding,
                "all_sources_task_owned": all(
                    Path(path).resolve().is_relative_to(pack)
                    for path in [*source_paths, *plugin_paths]
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


def _pinned_manifest_digests() -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in (MANIFESTS / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        pins[name.strip()] = digest
    return pins


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
        "num_classes": 37,
        "objective": ["ce", "mean"],
        "partition_count": 370,
        "primary": ["accuracy", "higher"],
        "secondaries": [["macro_f1", "higher"], ["log_loss", "lower"]],
        "task_data_path_id": "oxford_iiit_pet",
        "task_type": "classification",
    }


def test_every_committed_csv_matches_its_provenance_pin() -> None:
    """Every task-owned split or qualification manifest remains pinned."""
    pins = _pinned_manifest_digests()
    present = {path.name for path in MANIFESTS.glob("*.csv")}

    assert set(pins) == present
    for name, expected in pins.items():
        assert _sha256(MANIFESTS / name) == expected


def test_training_validation_and_final_identities_are_disjoint() -> None:
    """No image identity may cross the three scientific data roles."""
    role_ids: dict[str, set[str]] = {}
    for role in ("train", "validation", "final"):
        rows = (MANIFESTS / f"{role}.csv").read_text(encoding="utf-8").splitlines()
        role_ids[role] = {line.split(",", maxsplit=1)[0] for line in rows[1:]}

    assert role_ids["train"].isdisjoint(role_ids["validation"])
    assert role_ids["train"].isdisjoint(role_ids["final"])
    assert role_ids["validation"].isdisjoint(role_ids["final"])


def test_composition_paths_are_package_relative() -> None:
    """The task manifest must not point back into a SIDERIUS checkout."""
    document = yaml.safe_load(COMPOSITION.read_text(encoding="utf-8"))
    serialized = json.dumps(document, sort_keys=True)

    assert "examples/oxford_iiit_pet" not in serialized
    assert "configs/task_composition/pets" not in serialized
    assert "/home/" not in serialized
    assert "/tmp/" not in serialized


def test_task_package_contains_no_experiment_launcher() -> None:
    """Static task ownership must not absorb workflow treatment parameters."""
    assert not (PACK / "quickstart.sh").exists()
    assert not (PACK / "workflows").exists()
    assert LAUNCHER.is_file()


def test_experiment_dry_run_reaches_the_selected_framework_checkout(
    tmp_path: Path,
) -> None:
    """The experiment entrypoint must drive the selected framework without GPU work."""
    checkout = _siderius_checkout()
    workspace = tmp_path / "workspace"
    data_dir = tmp_path / "images"
    data_dir.mkdir()
    (data_dir / "probe.jpg").write_bytes(b"not decoded during dry-run")
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
    assert "[DRY-RUN] would exec" in completed.stdout
    assert (
        str((checkout / "sdsc_submission_scripts" / "run_one_iteration.py").resolve())
        in completed.stdout
    )
    assert str(COMPOSITION.resolve()) in completed.stdout
    assert f"--workspace {workspace}" in completed.stdout
    assert f"--data_dir {data_dir}" in completed.stdout

    commands = [
        shlex.split(line.strip())
        for line in completed.stdout.splitlines()
        if "run_one_iteration.py" in line
    ]
    assert len(commands) == 2
    expected_values = {
        "--run_name": "pets_qualification",
        "--max_rounds": "2",
        "--max_epochs": "1",
        "--trial_portion": "1.0",
        "--train_portion": "1.0",
        "--eval_portion": "1.0",
        "--formal_portion": "1.0",
        "--formal_train_portion": "1.0",
        "--formal_eval_portion": "1.0",
        "--validation_max_samples": "74",
        "--min_formal_batch_size": "1",
        "--allowed_output_types": "classifier",
        "--trial_vram_budget_gb": "8",
        "--formal_vram_budget_gb": "12",
    }
    for index, command in enumerate(commands, start=1):
        assert command[command.index("--start_iteration") + 1] == str(index)
        for flag, expected in expected_values.items():
            assert command[command.index(flag) + 1] == expected
