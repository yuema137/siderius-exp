# Candidate evaluation from the caller's process

The published composition selects `CandidateEvaluationMetric`: the task's
declared metric with no arithmetic, which refuses to execute unless a
complete evaluator is bound in the process that runs the tuner. This page
is that binding. Read it with the `SIDERIUS-RUN.md` in your workspace,
which names every concrete path.

## What crosses, and in which direction

| direction | what | how |
|---|---|---|
| caller → coordinator | one exported candidate directory | `tess-score --candidate-source … --candidate-id … --run-id …` through the fixed sudo route |
| coordinator → caller | one receipt JSON, readable by you, immutable after publication | the path `tess-score` prints |

The coordinator runs inference itself, over the complete validation split,
against the evaluator's own flux and truth. Nothing you compute is scored;
only what your exported model computes on the coordinator's side is.

## The complete-evaluation client

`experiments.phyts_tess.main_orchestrator.tess_evaluation.TessCandidateEvaluator`
implements the framework's candidate-evaluation executor. Its settings
(`TessEvaluationSettings`) name the installed command, your candidate root,
the coordinator's receipt root, the run id, the frozen metric declaration
and its digest, and the coordinator's uid. It verifies the whole requested
metric declaration before exporting or invoking anything.

Provide a research-side exporter `(request, new_destination) -> None`.
`TessNativeExporter` is the one for this task's contract: it reconstructs
the trained model through the framework's registry and checkpoint owner,
traces it on synthetic `[1, 1, 1024]` and `[B, 1, 1024]` inputs (no
validation curve is opened on your side), writes `contract.json`, and
proves the result loads through the scorer's own loader before anything
crosses. Choose `method="trace"` or `"script"` explicitly and an
`inference_batch_size` from 1 through 256.

```python
import hashlib, json, sys
from pathlib import Path

# The public runtime is a source distribution, not an installed package:
# put its root on the path from the run declaration, not from this file.
sys.path.insert(0, RUN["runtime_root"])

from core.generated_library import bind_generated_library_to_workspace
from execute_tools.evaluation_execution import bind_candidate_evaluation
from execute_tools.validation_execution import (
    ValidationDeployment, bind_validation_deployment,
)
from workflows.task_composition import (
    bind_run_task_composition, build_task_composition_ref, compose_run_task_bindings,
)
from nodes.ml_hyperparameter_tune_agent.ml_hyperparameter_tune_agent import (
    HyperparamTuningAgent,
)
from agent.schemas.hyperparam_tuning import HyperparamTuningInput
from experiments.phyts_tess.main_orchestrator.tess_evaluation import (
    TessCandidateEvaluator, TessEvaluationSettings, TessNativeExporter,
)

bind_generated_library_to_workspace(workspace)
composition = compose_run_task_bindings(RUN["composition"])
evaluation = TessEvaluationSettings.model_validate_json(
    Path(RUN["evaluation_settings"]).read_text()
)
validation = ValidationDeployment.model_validate_json(
    Path(RUN["validation_settings"]).read_text()
)
evaluator = TessCandidateEvaluator(
    evaluation, TessNativeExporter(method="trace", inference_batch_size=64)
)
request = HyperparamTuningInput(
    **request_fields,   # the tuner input per the toolkit's tuner reference
    task_composition_ref=build_task_composition_ref(composition),
    task_description=composition.task_description,
    data_dir=RUN["data_dir"],
)
with (
    bind_run_task_composition(composition, physical_data_root=RUN["data_dir"]),
    bind_candidate_evaluation(evaluator),
    bind_validation_deployment(validation),
):
    output = HyperparamTuningAgent().run(request)
```

Each parallel process initializes its own workspace and bindings; context
bindings do not transfer to a fresh process. Construct `request_fields`
from the toolkit's tuner input contract and the run's published execution
policy, never from defaults.

## What comes back

A valid result and a completed-but-ineligible result both return a
receipt; a transport failure raises. `tess_receipt.read_tess_evaluation`
accepts a receipt only for the exact candidate bytes, run and invocation
it was written for, and only when the coordinator's own eligibility fields
agree with its scoring and Health evidence; it never recomputes either.
The projection (`receipt_result`) yields the framework's
`CandidateEvaluationResult`: a `MetricResult` when scoreable, a
`NotScoreableResult` otherwise, the persisted Health gate results, and
`eligible_for_selection`. An ineligible evaluation is feedback, not an
error.

A scorer failure retains the exported candidate and writes bounded
stdout/stderr to `<workspace>/evaluation_diagnostics/<invocation>.json`.
Read that before retraining: if only transport failed, the trained
candidate can be sent again under a new candidate id.

## Before a substantial training attempt

Read the published `scripted_implementation.md` and
`scripted_model_export.md` contracts when connecting an implementation to
training, and check an untrained copy of a new architecture with the
exporter's round trip. The scorer loads on CPU; a trace that freezes a CUDA
device constant loads and then fails. This is a submission-format check,
not a constraint on architecture, loss or search strategy.

Retain, per candidate, what the receipt was computed from: the exported
directory as written, and the receipt path. The coordinator retains its own
snapshot and the receipt is immutable; yours is what you reason from.
