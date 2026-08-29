"""External acceptance witness for SIDERIUS issue #386."""

from __future__ import annotations

import argparse
import os
import warnings
from pathlib import Path


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

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "error",
            message="tidmad_data_config.yaml not found.*",
        )
        import workflows.model_exploration  # noqa: F401
        from workflows.task_composition import compose_run_task_bindings

        composition = compose_run_task_bindings(args.manifest)

    if type(composition.task_data_path).task_data_path_id != "naturebench_cancer_gene":
        raise RuntimeError("external task composition resolved the wrong data path")
    print("PASS: generic workflow import did not resolve TIDMAD configuration")


if __name__ == "__main__":
    main()
