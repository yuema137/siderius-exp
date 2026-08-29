"""External acceptance witness for SIDERIUS checkpoint 8be2874d."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import h5py


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--siderius-checkout", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument(
        "--subset-ref",
        default="cpdb,ltg",
        help="Comma-separated complete NatureBench networks to qualify.",
    )
    parser.add_argument(
        "--manifest",
        default=str(
            Path(__file__).resolve().parents[2]
            / "tasks"
            / "cancer_gene_identification"
            / "workflows"
            / "qualification"
            / "composition.yaml"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    siderius_checkout = Path(args.siderius_checkout).resolve()
    sys.path.insert(0, str(siderius_checkout))

    import core.sandbox_executor as sandbox_executor
    from execute_tools.task_data_path import EpochSamplingParams, ScopeBuildRequest
    from nodes.ml_hyperparameter_tune_agent.scope_acquisition import AttemptScopes
    from workflows.model_exploration import (
        lit_review_config_sha256,
        refuse_shipped_lit_review_config_on_composed_run,
    )
    from workflows.task_composition import (
        bind_run_task_composition,
        compose_run_task_bindings,
    )
    from workflows.task_config import get_task_description, load_task_config

    imported_framework = Path(sandbox_executor.__file__).resolve().parents[1]
    if imported_framework != siderius_checkout:
        raise RuntimeError(
            f"imported SIDERIUS from {imported_framework}, expected {siderius_checkout}"
        )

    composition = compose_run_task_bindings(str(Path(args.manifest).resolve()))
    if type(composition.task_data_path).task_data_path_id != "naturebench_cancer_gene":
        raise RuntimeError("external task composition resolved the wrong data path")

    data_root = Path(args.data_dir).resolve()
    selected_instances = tuple(
        part.strip() for part in args.subset_ref.split(",") if part.strip()
    )
    if not selected_instances:
        raise ValueError("--subset-ref must select at least one network")
    data_evidence: dict[str, dict[str, int]] = {}
    for instance in selected_instances:
        path = data_root / instance / "data.h5"
        if not path.is_file():
            raise FileNotFoundError(f"missing real NatureBench data file: {path}")
        if path.stat().st_size < 1_000_000:
            raise RuntimeError(f"refusing placeholder-sized data file: {path}")
        with h5py.File(path, "r") as handle:
            required_keys = {
                "network",
                "features",
                "mask_train",
                "mask_val",
                "mask_test",
                "y_train",
                "y_val",
            }
            missing_keys = sorted(required_keys - set(handle.keys()))
            if missing_keys:
                raise RuntimeError(f"{path} is missing HDF5 keys: {missing_keys}")
            train_mask = handle["mask_train"][:].astype(bool)
            val_mask = handle["mask_val"][:].astype(bool)
            test_mask = handle["mask_test"][:].astype(bool)
            if (train_mask & val_mask).any() or (train_mask & test_mask).any():
                raise RuntimeError(f"{path} has overlapping train and held-out masks")
            if (val_mask & test_mask).any():
                raise RuntimeError(f"{path} has overlapping validation and test masks")
            data_evidence[instance] = {
                "bytes": path.stat().st_size,
                "nodes": int(handle["features"].shape[0]),
                "train_nodes": int(train_mask.sum()),
                "validation_nodes": int(val_mask.sum()),
                "test_nodes": int(test_mask.sum()),
            }

    with tempfile.TemporaryDirectory(prefix="siderius_exp_checkpoint_") as temp:
        root = Path(temp)
        task_lit_config = root / "task_literature_review.yaml"
        task_lit_config.write_text(
            "enabled: true\nroot_papers: []\ndynamic_search:\n  enabled: false\n",
            encoding="utf-8",
        )

        with bind_run_task_composition(composition, physical_data_root=str(data_root)):
            if get_task_description(load_task_config()) != composition.task_description:
                raise RuntimeError(
                    "literature-review task context did not resolve from composition"
                )

            refuse_shipped_lit_review_config_on_composed_run(
                task_composition=composition,
                lit_review_enabled=True,
                lit_review_config_path=str(task_lit_config),
            )
            if lit_review_config_sha256(str(task_lit_config), enabled=True) is None:
                raise RuntimeError("task-owned literature-review config was not pinned")
            try:
                refuse_shipped_lit_review_config_on_composed_run(
                    task_composition=composition,
                    lit_review_enabled=True,
                    lit_review_config_path="configs/lit_review_config.yaml",
                )
            except ValueError:
                pass
            else:
                raise RuntimeError(
                    "composed run accepted the shipped task-specific config"
                )

            request = ScopeBuildRequest(
                round_kind="formal",
                selection_strategy="snapshot",
                portion=1.0,
                seed=0,
                subset_ref=args.subset_ref,
            )
            scopes = AttemptScopes(
                training=composition.task_data_path.build_training_scope(request),
                evaluation=composition.task_data_path.build_eval_scope(request),
            )
            training_dataset = composition.task_data_path.training_dataset(
                scopes.training,
                EpochSamplingParams(data_dir=str(data_root), epoch_seed=0),
            )
            for index, instance in enumerate(selected_instances):
                model_input, supervision = training_dataset[index]
                node_count = int((model_input[:, 0] > 0.5).sum().item())
                active_train_nodes = int((supervision[:, 1] > 0.5).sum().item())
                if node_count != data_evidence[instance]["nodes"]:
                    raise RuntimeError(
                        f"{instance} task data path changed the declared node count"
                    )
                if active_train_nodes != data_evidence[instance]["train_nodes"]:
                    raise RuntimeError(
                        f"{instance} task data path changed the training mask"
                    )
                data_evidence[instance]["packed_records"] = int(model_input.shape[0])

            captured: dict[str, list[str]] = {}

            def _capture(command, **_kwargs):
                captured["command"] = command
                raise SystemExit("argv captured")

            sandbox = sandbox_executor.TidmadSandbox(
                metadata_source="local",
                run_name="external_checkpoint",
                workspace=str(root / "workspace"),
                file_index=0,
            )
            with patch.object(
                sandbox_executor, "_run_observed_subprocess", side_effect=_capture
            ):
                try:
                    sandbox.execute_training(
                        exp_id="external_checkpoint_001",
                        run_name="external_checkpoint",
                        model_type="cancer_gene_reference_gnn",
                        m_cfg={
                            "model_type": "cancer_gene_reference_gnn",
                            "segmentation_size": 64,
                            "hidden_dim": 64,
                            "message_steps": 2,
                        },
                        t_cfg={
                            "epochs": 1,
                            "batch_size": 1,
                            "lr": 1e-4,
                            "optimizer_type": "adamw",
                            "device": "cpu",
                        },
                        l_cfg={
                            "loss_type": "custom",
                            "loss_name": "cancer_gene_masked_bce",
                        },
                        sample_set=None,
                        task_scopes=scopes,
                    )
                except SystemExit as exc:
                    if str(exc) != "argv captured":
                        raise

        command = captured.get("command", [])
        required = {
            "--task_scope_ref",
            "--task_eval_scope_ref",
            "--validation_requested_rows",
        }
        missing = sorted(required - set(command))
        if missing:
            raise RuntimeError(
                f"training child argv omitted composed scope fields: {missing}"
            )
        if "--sample_set_json" in command:
            raise RuntimeError(
                "external composed task unexpectedly emitted a legacy SampleSet"
            )

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "task_data_path_id": type(
                        composition.task_data_path
                    ).task_data_path_id,
                    "composition_fingerprint": composition.semantic_fingerprint,
                    "lit_review_task_config": "accepted_and_pinned",
                    "shipped_lit_review_config": "refused",
                    "training_scope_transport": "present_without_legacy_sample_set",
                    "real_data": data_evidence,
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
