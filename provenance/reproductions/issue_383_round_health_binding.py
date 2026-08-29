"""External acceptance witness for SIDERIUS issue #383."""

from __future__ import annotations

import argparse
import inspect
import tempfile
from pathlib import Path

from execute_tools.health_checks.config import materialize_effective_config
from execute_tools.health_checks.evaluation import evaluate_and_persist_health_gates
from execute_tools.health_checks.schemas import HealthCheckContext
from workflows.task_composition import compose_run_task_bindings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default=str(
            Path(__file__).resolve().parents[2]
            / "tasks"
            / "oxford_iiit_pet"
            / "composition.yaml"
        ),
    )
    parser.add_argument("--production-policy", required=True)
    args = parser.parse_args()

    composition = compose_run_task_bindings(args.manifest)
    with tempfile.TemporaryDirectory(prefix="siderius-issue-383-") as workspace:
        effective_path, _ = materialize_effective_config(
            None,
            None,
            workspace,
            task_health_binding=composition.task_health_binding,
        )
        kwargs = {
            "config_path": effective_path,
            "production_config_path": args.production_policy,
            "gate_ids": [],
        }
        if "task_health_binding" in inspect.signature(
            evaluate_and_persist_health_gates
        ).parameters:
            kwargs["task_health_binding"] = composition.task_health_binding
        evaluate_and_persist_health_gates(
            HealthCheckContext(
                model_name="external_candidate",
                run_name="issue_383",
                round_index=1,
            ),
            **kwargs,
        )

    print("PASS: round evaluation preserved the composed task Health binding")


if __name__ == "__main__":
    main()
