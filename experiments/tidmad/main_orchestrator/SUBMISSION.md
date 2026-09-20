# Reuse baseline candidate submission

Use the already-installed `tidmad-score` command and its existing narrowly
allowlisted sudo entrypoint, candidate contract, complete-band evaluator,
retention and collection. No new socket service is required for this release.

Read the frozen task's command help and submission instructions. Export the
native trained model using the existing certified candidate helpers, then submit
it using that interface. A successful tuner result is not a scoring receipt.
Preserve the candidate identity, original receipts and baseline recovery rules.

Do not modify the frozen scorer or its private-data permissions. Verify the
actual research account can invoke the installed command during short smoke.

The installed wrapper already supplies its internal `candidate` subcommand;
consult `tidmad-score --help` before constructing an invocation. Do not repeat
that token when the installed wrapper accepts candidate options directly.

`baseline_receipt.read_baseline_evaluation` reads the evaluator-owned `score.json`
returned by this route. Supply the expected band, candidate tree digest, run ID,
invocation ID and operator-selected evaluator UID. It checks receipt identity,
complete-band coverage and consistency of the evaluator's eligibility fields;
it does not recompute the metric or Health. A completed but ineligible evaluation
remains feedback, not a transport failure. Keep the original receipt, including
its detailed Health evidence. This reader alone does not connect native tuner
inference/scoring/Health to the protected evaluator.

Historical socket recovery tests at exp `85a2191` describe the withdrawn design;
they do not qualify the selected baseline submission route.

## Complete-evaluation client

`baseline_evaluation.BaselineCandidateEvaluator` implements the framework's
explicit candidate-evaluation executor. Its settings name the installed command,
band, original archive/feedback roots, research candidate directory, experiment
run ID and the frozen metric declaration plus its digest. It verifies the entire
requested metric declaration before exporting or invoking the evaluator.

Provide a research-side exporter with signature `(request, new_destination) ->
None`. It must reconstruct the actual trained model and write a complete original
candidate package there. `native_export.NativeTidmadExporter` supplies this
reconstruction for the frozen continuous-regression candidate contract. Select
`method="script"` or `method="trace"` explicitly and an evaluator-compatible
inference batch size. Using a synthetic exporter is transport testing only.

Each invocation has a fresh candidate ID and environment identity. Valid results
return an archive directory; completed but ineligible results return a feedback
JSON. Both are verified against the exact candidate bytes, run/invocation and
complete band before conversion to native metric/Health feedback. A nonfinite
score explicitly marked not scoreable is a scientific refusal; a nonfinite
score claimed scoreable is rejected. Original detailed receipts remain intact.

The original scorer exposes only its frozen primary metric. A request for
additional metrics is rejected before execution, never silently dropped.
The existing outer supervisor owns the run deadline and privileged transient
inference cleanup. This client adds no local-only timeout, because terminating
only the public wrapper would not certify cleanup of those privileged services.
Qualify that cleanup with the actual deployed supervisor before a formal run.


The native exporter uses the framework's existing registry constructor, checkpoint
path owner, cardinality and inference-dtype resolver. It requires the effective
loss configuration, restores checkpoint state strictly and runs only as the
research account. It retains native configuration, observed checkpoint/source
hashes and model/config source files; serialized execution is self-contained.
Source copies support diagnosis and do not claim a complete Python dependency
archive. A missing historical-inference sidecar does not prevent this export.

Before calling the scorer, it loads the exported model through the original
baseline loader and checks synthetic ADC inputs with the original decoder. This
adds no task-data access or new scoring formula. The full native call still needs
deployed qualification; local export success alone is not formal launch readiness.

## Check deployment compatibility before training

A native validator pass establishes its tested model contract; it does not certify
this deployment's serialized submission. Read the published
[`scripted_implementation`](../../shared/scripted_implementation.md) and
[`scripted_model_export`](../../shared/scripted_model_export.md) contracts when
connecting implementation to training. Both helpers run in the research worker,
without private data access. Use them before a substantial training attempt.

The H100 evaluator loads on CPU and moves the model to CUDA for inference. A trace
can pass CPU comparisons but freeze a CPU device constant and fail after that
move. Check both `execution_devices=("cpu", "cuda:0")`, with the selected script
or trace method, on an untrained copy and again during final export. This is a
submission-format check, not a requirement to choose a different architecture,
loss, search strategy or validation fraction. Do not change the frozen task.

For a new implementation, the existing native implementor can be called through:

```python
from experiments.shared.scripted_implementation import implement_for_scripted_export

qualified = implement_for_scripted_export(
    native_implementor, validated_implementor_request,
    examples=cpu_examples,  # explicit legal inputs; at least two for trace
    method="trace", execution_devices=("cpu", "cuda:0"),
)
implementation = qualified.implementation  # ordinary native ImplementorOutput
```

The wrapper returns no trained model and does not replace the native validator.
For a model already generated, construct its exact selected configuration with
the native registry and call `qualify_scripted_model(model.cpu().eval(),
cpu_examples, method=selected_method, execution_devices=("cpu", "cuda:0"))`.
This avoids another implementor/model-provider call just to run the check.
Persist the source/configuration and qualification result in the run workspace.
Changed model/configuration bytes need their own check; a result is not a blanket
claim about every future tuner configuration.

An evaluation-command failure retains its exported candidate and writes bounded
stdout/stderr to `<workspace>/evaluation_diagnostics/<invocation>.json`.
Inspect that evidence before deciding to retrain. If only evaluation transport
failed, the already trained candidate can be sent through the existing scorer
again with a new candidate ID. A model-code change requires fresh compatibility
and provenance checks; do not declare altered code equivalent to certified
training merely because weights still load.

## Public task composition

`public_composition.public_candidate_composition(frozen_input, analysis_path=None)`
creates an additional manifest payload referencing the original frozen task.
Write it outside the frozen input tree. It preserves public declarations and
rebases their paths, while selecting the framework's `CandidateEvaluationMetric`
instead of importing private scoring code. No task files are rewritten.

The baseline's public training files contain compact positions 0–19, whereas
the frozen training pool declares original PSD segment IDs. The additional
manifest therefore selects `CompactFrozenPoolDataPath` with the original frozen
manifest as configuration. It loads that manifest's actual data-path plugin,
delegates its scientific scope construction and validation reading, and maps
only training read offsets through the pinned original pool list. It rejects
out-of-pool IDs and files whose shape/dtype do not match the compact layout.
Original scope serialization remains unchanged; storage-byte estimates use the
20-slot physical pool. The original workflow data-path implementation is intact.

Publish this task-side adapter to research and native training processes with
the other public runtime clients. Select the composed ID
`tidmad_compact_frozen_training_pool` in the protected launch policy; an old
`tidmad_frozen_training_pool` policy correctly refuses that different selection.

Compose this manifest through `compose_run_task_bindings`, and bind both its
task composition and `bind_candidate_evaluation(BaselineCandidateEvaluator(...))`
in the process calling the tuner. The candidate metric refuses execution without
that evaluator binding. Bind protected per-epoch validation separately; it does
not replace the scientific candidate score. Analysis defaults off; an explicit
analysis config still requires the treatment's prior authorization/publication.

## Research-process binding example

### Publish the public clients first

The complete exp checkout is operator-only: it contains Full advice, private
scorer source and Git history. Do not make it the research account's import root.
From the selected operator checkout, call
`public_runtime.publish_public_runtime(repository_root, frozen_input, new_output)`.
This writes an explicit set of public clients and their source hashes, exact
infra/exp identities and unchanged dependency lock. It links `tasks` to the
already-frozen public input, refusing a task view containing private scoring
source. It does not copy Git history, advice, an environment, or task bytes.

Create the output's own environment with
`uv sync --group dev --frozen --python <qualified-interpreter>` from that
directory; use the qualified deployment Python, not an implicit host default,
and never reuse the operator checkout's environment. The output is
a source distribution with `public-runtime.json` provenance, not a Git clone.
Use its own Python from its root for the research process. Generate the public
composition outside frozen input and set its `task_data_path.file` to this
distribution's `experiments/tidmad/main_orchestrator/compact_training.py`.
The protected launcher remains installed from the separate operator checkout.
The public distribution also contains the native training entry, target-free
metadata probes and numeric workers with their shared dependencies. Bind the
protected runtime's research Python and framework entrypoint to this public
environment, with the public distribution as the module working directory.
Before training, run its Python with
`-B -m experiments.shared.native_training_entry --help` as the research UID;
successful client imports alone do not establish that the training entry exists.

Publication alone does not prove host access isolation. Before starting an
actual NoPrior coding agent, make all operator checkouts, their Git objects,
advice and old qualification artifacts inaccessible to its UID; verify both
successful public-client imports and denied reads with that actual UID. Keep
the published runtime and frozen input immutable. Do not change baseline GPU,
network, public data, scratch-space or scoring permissions to achieve this.

The operator publishes the additional public manifest and two public JSON
configuration files: one matching `BaselineEvaluationSettings`, the other
matching `ValidationDeployment`. These contain paths, identities, the installed
launcher and deadline; never credential values or private task implementation.
The launcher/policy must already be installed and qualified. Creating these
JSON files does not install that boundary.

The metadata probe needs writable temporary storage to materialize captured
model and loss plugins. Preserve a writable `/tmp` in its namespace; mounting
host scratch read-only over the namespace's temporary filesystem breaks plugin
admission before training. Verify temporary-file creation as the actual probe
UID, in addition to checking imports and denied private-data reads.

Bind caller identity from the actual baseline service's `User` and `Group`,
not just the account's login defaults. The qualified host's service uses
`baseline-results` as its primary group. Its inherited `/tmp` mount is only
16 MiB; map native temporary storage to the existing writable baseline scratch
directory instead. Permit coordinator writes only to its root-owned run-state
directory in addition to the baseline's existing writable paths. Qualify this
inside a service with the actual baseline isolation properties: a successful
interactive sudo invocation does not test those inherited mounts or identities.

The sudo entrypoint must preserve the source-locator environment keys declared
by `experiments.shared.native_launcher._SOURCE_ENVIRONMENT_KEYS`. Configure
`env_keep` for that command only. These values locate untrusted model/loss
sources for capture and admission; they do not authorize arbitrary imports or
private-data access. Do not enable unrestricted `SETENV` or forward `PYTHONPATH`
or provider credentials to the native training subprocess.

Choose the protected policy's snapshot allowance from the deployment's existing
memory budget and use that same value for the public validation binding. The
10 MB allowance used in tiny-model smoke fixtures is not a formal-run setting:
a 328-million-parameter FCNet alone has about 1.31 GB of serialized state.
Keep state size distinct from validation batch count and the experiment clock;
do not introduce a small-model restriction by copying diagnostic configuration.

In a fresh research process, use the public distribution's own Python and
initialize the chosen workspace before registry-bearing native imports:

```python
import sys
from pathlib import Path

# The public runtime is a source distribution, not an installed exp package.
# A script in your own workfolder needs its source root on the import path.
# Derive that root from THIS public runtime's .venv; do not borrow a checkout.
sys.path.insert(0, str(Path(sys.prefix).parent))

from core.generated_library import bind_generated_library_to_workspace

# These paths are supplied by the deployment; workspace is this branch's storage.
bind_generated_library_to_workspace(workspace)

from agent.schemas.hyperparam_tuning import HyperparamTuningInput
from execute_tools.evaluation_execution import bind_candidate_evaluation
from execute_tools.validation_execution import (
    ValidationDeployment, bind_validation_deployment,
)
from workflows.task_composition import (
    compose_run_task_bindings, build_task_composition_ref, bind_run_task_composition,
)
from nodes.ml_hyperparameter_tune_agent.ml_hyperparameter_tune_agent import (
    HyperparamTuningAgent,
)
from experiments.tidmad.main_orchestrator.baseline_evaluation import (
    BaselineCandidateEvaluator, BaselineEvaluationSettings,
)
from experiments.tidmad.main_orchestrator.native_export import NativeTidmadExporter

composition = compose_run_task_bindings(str(public_manifest))
evaluation = BaselineEvaluationSettings.model_validate_json(
    Path(evaluation_settings_path).read_text()
)
validation = ValidationDeployment.model_validate_json(
    Path(validation_settings_path).read_text()
)
evaluator = BaselineCandidateEvaluator(
    evaluation,
    NativeTidmadExporter(
        method="trace", inference_batch_size=32,
        execution_devices=("cpu", "cuda:0"),
    ),
)
# request_fields holds the agent's native input fields: model, scope, budgets,
# storage, provider, seed/model-I/O, etc. Its storage workspace must be workspace.
# Do not duplicate the three composition/data fields supplied below.
request = HyperparamTuningInput(
    **request_fields,
    task_composition_ref=build_task_composition_ref(composition),
    task_description=composition.task_description,
    data_dir=str(public_training_root),
)
with (
    bind_run_task_composition(composition, physical_data_root=str(public_training_root)),
    bind_candidate_evaluation(evaluator),
    bind_validation_deployment(validation),
):
    output = HyperparamTuningAgent().run(request)
```

Launch a saved script with `<public-runtime>/.venv/bin/python /path/to/script.py`.
Its working directory can remain the agent's own workfolder. Selecting that
interpreter alone does not make the public `experiments` sources importable;
the explicit same-environment bootstrap above supplies them without `PYTHONPATH`.

Construct `request_fields` using the toolkit's tuner input contract and the
run's published execution settings. The example selects tracing explicitly for
the frozen regression export contract; it does not prescribe an architecture,
loss, number of calls or scheduling strategy. Each parallel process initializes
its own workspace and bindings. Context bindings do not transfer to a fresh
process automatically. Preserve native output and original scoring receipts.

For tasks declaring historical inference, native training's artifact contract
requires the registered model and configuration classes to be defined in the
same plugin source file. A built-in model whose classes live in separate files
does not satisfy that contract merely because it trains successfully. When
reusing such a model, supply a normal registered plugin with both classes and
the documented single-config constructor. For a fixed regression architecture,
select its regression head explicitly rather than inheriting a classification
default. This is the existing artifact/constructor contract, not an additional
orchestrator restriction on model architecture or custom loss selection.
