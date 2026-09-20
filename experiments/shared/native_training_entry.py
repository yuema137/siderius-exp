"""Enter installed native training from the deployment checkout's module path.

Launch with the exact checkout's interpreter and its protected root as cwd:
python -m experiments.shared.native_training_entry <native training arguments>
This makes the deployment client importable without PYTHONPATH, editable installs
from other checkouts, or changes to the frozen scientific package.
"""

import os
import runpy
import sys
from contextlib import ExitStack
from pathlib import Path

from core.sandbox_executor import sandbox_records_dir
from execute_tools.trained_model_artifact import training_artifact_candidate_path
from execute_tools.training_cli import build_training_parser

from experiments.shared.epoch_model_worker import (
    EpochModelSource,
    bind_epoch_model_source,
)
from experiments.shared.native_loss_binding import AdmittedLossSource, bind_native_loss
from experiments.shared.native_training_provenance import (
    publish_training_candidate_sources,
)


def main() -> None:
    with ExitStack() as bindings:
        factories = {
            "--admitted-model-source-fd": (EpochModelSource, bind_epoch_model_source),
            "--admitted-loss-source-fd": (AdmittedLossSource, bind_native_loss),
        }
        seen = set()
        while sys.argv[1:2] and sys.argv[1] in factories:
            flag = sys.argv[1]
            if flag in seen or len(sys.argv) < 3:
                raise ValueError("admitted source descriptor missing or repeated")
            seen.add(flag)
            with os.fdopen(int(sys.argv[2]), "rb") as source:
                payload = source.read(4194305)
            if len(payload) > 4194304:
                raise ValueError("admitted source exceeds limit")
            schema, bind = factories[flag]
            bindings.enter_context(bind(schema.model_validate_json(payload)))
            del sys.argv[1:3]
        arguments = build_training_parser().parse_args(sys.argv[1:])
        runpy.run_module(
            "execute_tools.train_engine_sandbox", run_name="__main__", alter_sys=True
        )
        publish_training_candidate_sources(
            training_artifact_candidate_path(
                Path(sandbox_records_dir(arguments.sandbox_dir)) / arguments.run_name,
                arguments.exp_id,
            )
        )


if __name__ == "__main__":
    main()
