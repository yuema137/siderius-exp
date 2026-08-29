"""External acceptance witness for SIDERIUS issue #384."""

from __future__ import annotations

import argparse
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import h5py
import numpy as np


def _write_fixture(data_root: Path) -> None:
    target = data_root / "cpdb"
    target.mkdir(parents=True)
    with h5py.File(target / "data.h5", "w") as handle:
        handle.create_dataset("features", data=np.arange(256, dtype=np.float32).reshape(4, 64))
        handle.create_dataset(
            "network",
            data=np.asarray(
                [
                    [0, 1, 0, 0],
                    [1, 0, 1, 0],
                    [0, 1, 0, 1],
                    [0, 0, 1, 0],
                ],
                dtype=np.int8,
            ),
        )
        handle.create_dataset("mask_train", data=np.asarray([1, 0, 0, 0], dtype=np.int8))
        handle.create_dataset("y_train", data=np.asarray([1, 0, 0, 0], dtype=np.float32))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default=str(
            Path(__file__).resolve().parents[2]
            / "tasks"
            / "cancer_gene_identification"
            / "workflows"
            / "formal"
            / "composition.yaml"
        ),
    )
    args = parser.parse_args()
    plugin_dir = str(Path(args.manifest).resolve().parents[2] / "plugins")
    os.environ["SIDERIUS_PLUGIN_DIRS"] = plugin_dir
    os.environ["SIDERIUS_LOSS_DIRS"] = plugin_dir

    from agent.skills.evaluate_vram_skill.preflight_adapter import run_production_preflight
    from core.hardware_context import HardwareContext
    from execute_tools.task_data_path import (
        EpochSamplingParams,
        ScopeBuildRequest,
        resolve_task_scope_capability,
    )
    from workflows.task_composition import compose_run_task_bindings

    composition = compose_run_task_bindings(args.manifest)
    capability = resolve_task_scope_capability(composition.task_data_path)
    request = ScopeBuildRequest(
        round_kind="trial",
        selection_strategy="snapshot",
        portion=1.0,
        subset_ref="cpdb",
        target_partitions=(),
        task_parameters={"seg_size": 10_000},
    )
    scope = capability.build_training_scope(request)

    try:
        from agent.skills.evaluate_vram_skill.isolated_probe import TaskProbeDataSpec
    except ImportError:
        TaskProbeDataSpec = None  # type: ignore[assignment,misc]

    if TaskProbeDataSpec is None:
        from agent.skills.evaluate_vram_skill.wrapper import run_skill

        legacy = run_skill(
            None,
            model_type="cancer_gene_reference_gnn",
            model_config={
                "batch_size": 1,
                "segmentation_size": 10_000,
                "hidden_dim": 8,
                "message_steps": 1,
            },
            train_config={"batch_size": 1, "optimizer": "adam"},
            loss_config={
                "loss_type": "custom",
                "loss_name": "cancer_gene_masked_bce",
            },
            vram_budget_gb=40.0,
            hardware_context=type(
                "Hardware",
                (),
                {
                    "usable_cap_bytes": 40 * 1024**3,
                    "usable_cap_gb": 40.0,
                    "total_memory_bytes": 48 * 1024**3,
                    "total_memory_gb": 48.0,
                    "device_name": "synthetic-probe-device",
                    "device_available": True,
                },
            )(),
            model_io_contract=composition.forward_contract.model_io,
        )
        raise RuntimeError(f"semantic VRAM probe failed: {legacy}")

    with tempfile.TemporaryDirectory(prefix="siderius-issue-384-") as root:
        root_path = Path(root)
        data_root = root_path / "data"
        _write_fixture(data_root)
        task_probe_data = TaskProbeDataSpec(
            manifest_path=str(Path(args.manifest).resolve()),
            semantic_fingerprint=composition.semantic_fingerprint,
            training_scope_payload=capability.serialize_scope(scope),
            sampling=EpochSamplingParams(data_dir=str(data_root), epoch_seed=7),
        )
        hardware = HardwareContext(
            device_name="synthetic-probe-device",
            total_memory_bytes=48 * 1024**3,
            compute_capability=(9, 0),
            multiprocessor_count=1,
            torch_version="synthetic",
            hostname="external-witness",
            device_available=True,
            discovered_at=datetime.now(UTC),
        )
        result = run_production_preflight(
            model_type="cancer_gene_reference_gnn",
            model_config={
                "batch_size": 1,
                "segmentation_size": 10_000,
                "hidden_dim": 8,
                "message_steps": 1,
            },
            train_config={"batch_size": 1, "optimizer": "adam"},
            loss_config={
                "loss_type": "custom",
                "loss_name": "cancer_gene_masked_bce",
            },
            vram_budget_gb=40.0,
            hardware_context=hardware,
            workspace=root_path,
            label="issue_384",
            plugin_dir=plugin_dir,
            loss_dir=plugin_dir,
            model_io_contract=composition.forward_contract.model_io,
            task_probe_data=task_probe_data,
            deadline_seconds=60.0,
        )

    if result.get("status") == "error" or "no labeled node rows" in str(result):
        raise RuntimeError(f"semantic VRAM probe failed: {result}")
    print("PASS: VRAM admission measured the task-valid semantic target")


if __name__ == "__main__":
    main()
