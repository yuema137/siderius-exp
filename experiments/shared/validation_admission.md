# Private-loss admission contracts

These modules implement admission and review contracts, not a deployed training
or validation service. Frozen task/evaluation packages and baseline scoring are
unchanged. Custom objectives remain supported; review is automatic, without a
human approval loop during the run.

`ValidationLossRequest` selects only a training record. Trusted worker settings
select registry location, owner, run, framework revision, composition and review
policy. Never accept these settings from a research request. The registry and
its parent must be inaccessible for research writes. Only the trusted training
executor may publish native epoch-completion records, after observing training
and sealing the corresponding model snapshot. A caller-authored artifact or
successful restore is not evidence that this executor trained the model.

The objective reference identifies a bundle of exact source, dependencies and
effective parameters. The matching automatic review must contain source,
isolated synthetic-execution and purpose-check evidence. A missing stage,
negative result, changed objective or changed policy cannot authorize execution.
Retain rejected receipts and reasons too. An approval is not a confidentiality
proof and does not authorize other analysis operations.

`review_objective_purpose` uses the existing `LLMBridge.generate` interface and
never executes supplied source. Send only code/configuration, never private
samples. Its result binds the sent material and review instructions by hash.
Malformed/failed calls do not approve. Supply exact provider/model/effort from
the deployment and persist them with request/result evidence.

## Still required before deployment

- Trusted epoch snapshot issuance, objective bundle assembly and file verification.
- Bind the implemented review stages and protected publication to the actual launcher; the purpose verdict alone is insufficient.
- Protected model/loss workers, with only allowed aggregate loss/status returned.
- Native epoch-history integration, existing baseline candidate submission and
  the requested real H100 smoke. Current unit tests do not qualify these paths.

## Repeated validation cost

`validation_training_execution.run_admitted_native_training` connects an
already-admitted native invocation to `serve_validation_epoch` until the child
exits. It preserves the native exit status, supports early runtime rejection
without waiting for an epoch, and applies one continuing deadline. The existing
tuner remains responsible for interpreting result files and rejection receipts.
`AdmittedEpochExecutor` constructs the model and builtin/reviewed objective workers,
calls the native estimator, and records per-epoch worker startup and validation
times. Its `AdmittedEpochPlan` must come from protected launch inputs, never the
research request. Each invocation needs a separate protected diagnostics folder.

Two-epoch synthetic native training exercises this production execution path for
builtin and custom objectives. Caller authentication, input/source admission,
worker mount/Unix identity configuration and the installed H100 service remain
deployment responsibilities; these tests do not establish those boundaries.

Review belongs to objective admission, not every epoch. Within the run, reuse
the approved receipt for identical source, dependencies, effective parameters
and review policy. New model weights do not require another objective review.
Each validation still checks native training/snapshot identity. The repeated
path must not call an LLM, reinstall an environment or restart training.

This is an integration requirement, not a claim that caching or the worker is
already deployed. Measure one-time review separately from native forward/loss
and additional transfer/IPC/setup time in the short H100 smoke. Local metadata
lookup timing alone does not establish end-to-end overhead.

## Isolated synthetic numerical entrypoint

Invoke `python -m experiments.shared.objective_numerical_review` inside the
already-confined worker. Feed one `NumericalReviewRequest` as JSON on stdin;
stdout contains one `NumericalReviewResult`. The deployment supplies task-owned
tiny numeric fixtures and exact effective parameters. No real samples belong
in the request. The request hash includes the source, parameters, fixtures and
contracts. Results include numerical-check wall time; the launcher separately
measures total process time and enforces its timeout.

The worker uses the native custom-loss validator, not a second numerical
implementation. Candidate stdout is redirected to worker stderr. Only the
launcher establishes filesystem/network/process confinement and retains
evidence; this Python entrypoint is not a sandbox. A numerical pass is only
one review stage and cannot replace source/purpose review or model provenance.
Run this once for objective admission, never once per training epoch.

## One-time review pipeline

`objective_review_pipeline.review_objective` runs source, confined numerical and
purpose checks in that order. Earlier refusal skips later calls and records the
skip; timeouts, malformed worker results and mismatched numerical request hashes
produce rejection evidence. Numerical source and parameters must match the
reviewed material before any effectful stage. The returned bundle contains the
receipt, each stage's payload/hash, and coordinator-measured stage wall time.

The deployment must supply the confined numerical-worker callable and existing
LLM gateway, include provider/runtime/fixture settings in the policy identity,
and persist the entire bundle under protected ownership before publishing its
receipt. This routine does not install a worker or persist authority itself.
Call it on objective admission; subsequent epochs reuse the protected matching
receipt through validation admission rather than rerunning this pipeline.

## Publishing review evidence

`validation_admission.publish_automatic_review` is called only by the trusted
review coordinator, with its own `AutomaticReviewBundle`. It verifies material
and evidence hashes, saves the full source/parameters/synthetic request and stage
evidence, then atomically publishes the receipt read by `admit_validation_loss`.
Research-submitted bundles must never be passed to this function as authority.

Files are owner-only. The registry owner must be the trusted coordinator's
effective Unix identity and its parent must remain protected. A short directory
lock serializes publication only; epoch reads acquire no lock and execute no
review. Identical duplicate publication succeeds, conflicting review IDs refuse,
and a failed evidence write cannot publish an approval. Native training-record
issuance and isolated loss execution are still separate deployment obligations.

## Restoring the reviewed loss in its worker

`reviewed_objective_worker.restore_reviewed_objective` runs only after worker
confinement. It verifies the expected objective/policy and complete review bundle,
loads the reviewed plugin source through the native explicit-path loader, applies
its effective configuration, and restores exact numeric criterion state and mode.
It never deserializes a pickled loss module. The approved dependency runtime must
be mounted by the launcher. The caller supplies state from the trusted native
epoch path; this function alone cannot certify its provenance.

Synthetic isolated execution verifies this reconstruction but does not qualify
private-data access or real task validation. A production worker must remain
confined for its whole lifetime, including subsequent loss calls.

## Persistent numerical worker calls

`python -m experiments.shared.reviewed_objective_worker --config <operator-json>`
constructs the approved objective once, then serves numerical calls until EOF,
failure or its continuing deadline. `ObjectiveWorkerConfig` selects protected
review/state files, expected identities, device, mode and deadline. The state file
is JSON mapping names to `validation_module_protocol.TensorPayload`, not pickle.
Configuration paths and launch authority are operator-owned, never research
request arguments. The launcher must establish confinement before Python starts
and terminate the whole worker group on timeout or cancellation.

`validation_module_peer.ModulePeer` is a private-coordinator-side module proxy.
The protocol carries bounded numerical tensors, call identities and shared RNG
state; it preserves ordering between model and objective calls. No returned
targets, candidate state or post-validation RNG may be forwarded to the research
controller. Candidate stdout and errors remain in private worker stderr; only
structured failure codes traverse the result channel.

The call loop can reuse an initialized model or objective.
`python -m experiments.shared.native_model_worker --config <operator-json>`
restores an existing certified native model with the existing
`native_model_restore` contract, then serves model calls through the same loop.
`NativeModelWorkerConfig` supplies the protected artifact root, reference,
approved plugin, device, continuing deadline and frame bound. Registry imports
and candidate stdout are redirected to private stderr before model loading.
The source/restoration context remains alive through all calls.

This entry point inherits the native restoration adapter's supported plugin and
inference contracts; it does not add support for packaged plugins or metadata
adapters. It consumes an existing artifact and does not establish that an
in-progress epoch genuinely completed training. Genuine epoch provenance, task
materialization and complete native client integration still need deployment
wiring. Protocol/component tests do not establish those.

## Native invocation channel

`native_training_channel.launch_native_training_channel` creates a private
socket pair for one operator-launched native child. The parent endpoint stays
with the deployment, and only the child endpoint is inherited. There is no
listening pathname for an agent to connect to. The helper verifies the configured
interpreter/entrypoint and replaces the research-side validation binding with
the operator-selected factory/settings plus the inherited descriptor. Parallel
invocations receive separate endpoints. The existing outer process group is
preserved; the context closes endpoints and reaps its direct child on failure.

The caller still supplies protected policy, confinement, sanitized environment,
continuing deadline, group cancellation and task/path admission. The channel
binds messages to that launched invocation; it does not prove that arbitrary
candidate code honestly executed optimizer steps. Do not accept a caller-made
channel/session or its epoch counters as protected training authority.

For this non-packaged exp checkout, use operator-selected
`entry_module="experiments.shared.native_training_entry"` with the protected
checkout root as `cwd`. The entry runs the installed native training module,
preserving native argparse, while keeping deployment modules discoverable.
Use the checkout's own frozen interpreter. No `PYTHONPATH` override is needed.

This is a launcher helper, not an installed privileged CLI or a complete
validation client/service. Numerical requests, trained state admission and the
private evaluator boundary still require integration before deployment.

## Transient model state

`validation_snapshot.sealed_tensor_state` copies plain dense tensor state into
a Linux memory file and seals it against writing, resizing and further seal
changes. The context owns the descriptor and closes it on exit. A launcher can
transfer the descriptor to a confined model worker, which restores with
`torch.load(..., weights_only=True)` and strict native state loading. The helper
does not issue training provenance, authorize a request, or transfer descriptors
by itself; it is not yet wired into the private validation service.

Pause optimizer updates while taking a snapshot. The explicit byte bound counts
tensor payload, not serialization metadata or peak host memory. Keep formal
checkpoints durable; this ephemeral representation only avoids repeated disk
writes for validation. Do not deserialize candidate snapshots in the private-data
coordinator. The Linux implementation also supports managed Python builds that
omit `os.memfd_create` and the `fcntl` seal constants.

`validation_descriptor_transport.send_snapshots` passes the model and objective
snapshot descriptors plus bounded metadata over the inherited Unix channel.
`receive_snapshots` checks both descriptors are regular, bounded and sealed
against write/resize/seal changes; its context closes them on completion,
invalid messages and timeout. Descriptor receipt uses close-on-exec, so the
launcher must deliberately pass them onward to a confined worker. The private
coordinator checks metadata/authority before doing so and never deserializes
their tensor contents. Metadata must still be validated against the service's
request schema; immutable bytes alone do not establish training provenance.

Transport tests cover repeated distinct snapshots in one real subprocess and
descriptor cleanup after truncated/malformed/oversized/unsealed input. This
transport is used by `InheritedValidationClient` for the epoch exchange below.
It is not an installed private validation service.

## Inherited epoch client

`InheritedValidationClient` accepts a launcher-owned descriptor and continuing
deadline, task-owned scope serializer and row-declaration callback. It sends
typed configuration/scope/epoch/RNG metadata plus sealed model/objective tensor
state. The service must separately match these to its admitted invocation,
review and source identities; the client metadata does not supply authority.

The client receives only typed batch row counts/timings, aggregate result or
fixed refusal codes. It feeds the existing native verifier per sample and calls
`on_verified` during the pass. Each batch progress event requires a client
acknowledgement after allocation/verification callbacks, before the service
continues. Sequence/row mismatch, refusal or callback/transport failure closes
the channel, which cannot then be reused. Result/diagnostic payloads still obey
the existing native `ValidationExecutionResult` contract.

The parent requires row declaration before the native child and its channel
exist. Therefore the callback must be task-owned and independent of private
sample reads or the inherited child descriptor. A production parent factory,
protected service-side admission and execution loop still require wiring.
The client tests use a synthetic service and real SGD snapshots; they do not
qualify actual task data or a full native training deployment.

## Admitted epoch execution

`validation_epoch_execution.execute_admitted_epoch` runs the existing native
validation estimator with two `ModulePeer` instances, task-owned data access
and an already-admitted scope. It does not import candidate code or reconstruct
candidate objects in the coordinator. The caller verifies source/review/scope
identity, provisions isolated workers and supplies the task's declared dynamic
observable session when present. No client-provided field grants authority.

`ValidationProgressRelay` forwards the native batch timing through the epoch
protocol and waits for the client's sequence-matched acknowledgement. The
native verifier remains in the training client. Execution checks complete row
coverage and returns only native aggregates and declared observable values or
failure names. The coordinator restores its RNG state even when acknowledgement
or execution fails. This callable still needs protected service orchestration
and per-epoch worker construction/state binding; it is not a deployed endpoint.

## Epoch model reconstruction

`python -m experiments.shared.epoch_model_worker --config <operator-json>`
constructs a model from an operator-frozen `EpochModelSpecification` and loads
the inherited sealed tensor snapshot. It uses native config validation,
registered construction and strict state loading, with explicit source and
constructor identities. Bundled models use the installed source identity;
single-file plugins use the frozen source bytes. For packaged models,
`plugin_package` supplies an operator-staged root and the native `MemberIdentity`.
The worker checks the whole declared package before import and keeps
`bind_code_package` active through construction and numerical calls, preserving
relative imports. The operator must mount this staged package read-only; the
worker does not infer or fetch dependencies.

The worker needs no final trained-model artifact, so a completed first epoch can
be validated before training finishes. It holds source context and the model
for all batch calls until EOF/deadline. Snapshot seal/size validation has one
shared owner; only the confined worker calls the weights-only tensor loader.
The operator launcher must freeze this specification from the admitted native
invocation and establish confinement before Python starts. A caller-authored
specification with internally matching hashes is not training authorization.

## Parent and child client binding

`experiments.shared.validation_client_factory:create_validation_client` is the
explicit research-side `ValidationDeployment.factory`. Its settings declare a
public `row_declaration` callable, absolute `deadline_epoch`, metadata/state byte
limits, and an optional inherited `channel_fd`. The native parent can declare
workload without a channel. Only the trusted launcher installs the child's
channel; attempting validation without it refuses instead of reading local data.
The client resolves scope serialization through the currently bound task.

For TIDMAD, the experiment-owned declaration is
`experiments.tidmad.main_orchestrator.validation_rows:declared_rows`. It counts
ML windows from public scope/profile metadata without opening data, and handles
file-loaded task classes through the task's canonical serialization contract.
Parity tests compare the declaration with the unchanged task materializer.
Other tasks supply their own declaration callable; the generic client contains
no TIDMAD parsing. Neither this public count nor client-selected settings grant
private access: the service must independently admit the task scope, selected
model/objective and native invocation before executing any validation.

## Epoch transaction routing

`validation_epoch_service.serve_validation_epoch` receives two sealed snapshots,
validates metadata against an `AdmittedValidationWorkload`, then invokes the
private executor with a live progress relay. The workload must come from the
protected launcher after source and objective-review admission; constructing it
from the received request would bypass this boundary. Exact model config, loss,
scope, device, batch size, row count and native epoch/step progression are checked
before execution. Successful calls return the next sequence number. A failed
call raises locally and sends only a fixed refusal code when the channel and
remaining deadline allow it; exception messages must remain in private logs.

The supplied executor still owns confined model/objective worker launch and
calls `execute_admitted_epoch` with the protected task binding. This transaction
function does not install that launcher or qualify deployment. Local socket tests
cover two consecutive epochs, configuration/progression refusal before executor
entry, and sanitization of a private executor exception.

## Numeric worker process lifetime

`validation_worker_process.launch_validation_worker` routes typed model/objective
configs to their fixed module entrypoints, passes only the selected snapshot FD,
and constructs a numeric `ModulePeer`. Config and stderr files are exclusive,
owner-only files in the protected job directory; stderr must never be copied into
the research-visible response. The context reaps the direct worker on normal EOF
or coordinator failure and exposes startup wall time for qualification evidence.

The caller supplies the protected interpreter, sanitized environment and actual
confinement prefix with approved mounts and process/network isolation. Empty
prefixes are for synthetic tests only. Keep the existing outer process-group
deadline; this helper is not a replacement supervisor. The config path must be
visible at the same path inside the worker mount namespace. Per-epoch/per-role
paths must be distinct. Launch routing does not establish training provenance,
review authority or authorization to access private task data.

## Native builtin objectives

`builtin_objective_worker` uses the installed framework's `get_criterion` for
SmoothL1, CE, focal and class-weighted focal. It binds the exact native source
file hash and LossConfig supplied by the admitted launch, restores the sealed
numeric criterion state, then serves the same numeric worker protocol. Optional
CE/focal class-weight buffers must exist at construction before strict loading;
the worker restores them from the training snapshot rather than dropping them.

Custom loss routing is rejected by this configuration and continues through
`reviewed_objective_worker` with its approval bundle. The builtin source hash is
a runtime binding, not automatic review or proof of training. The same protected
launcher, confinement and scope admission obligations apply. Actual subprocess
parity tests cover all four builtin routes, weighted/unweighted variants and
non-default loss parameters/reduction.

## Native effective objective parameters

Before assembling a custom objective review, run
`python -m experiments.shared.native_objective_metadata` in a target-free,
confined process. Send an `ObjectiveMetadataRequest` containing the captured
single-file source and expected loss name. It uses the native plugin loader and
`Config()` construction used by current training, and returns source SHA-256,
effective parameters, target dtype and optional reduction as typed JSON.
Candidate import output goes to stderr; constructing the loss is unnecessary.

Verify the returned source identity against the protected capture, and build
both review material and its numerical request from those effective parameters.
Run this once for an immutable objective, never per epoch. It executes candidate
imports/default factories, so it must not run inside the private-data coordinator.
The launcher owns its timeout and confinement. This metadata is not approval;
source/numerical/purpose review and native invocation binding remain required.

## Review once for an exact native objective

`review_native_objective_once` binds captured source, native metadata, effective
parameters and the numerical request before running automatic review. Its cache
identity includes the run, policy, complete material, metadata, numerical fixture
and allowed imports. A protected per-identity lock prevents parallel branches
from duplicating the same review; different objectives use different locks.
Both approvals and rejections retain complete evidence. Reuse validates the
saved bundle and published receipt; an evidence-only interrupted publication can
finish without another model call. Conflicting records refuse.

Only the trusted launcher may supply these inputs and the protected registry.
The caller owns timeout/cancellation while waiting for review or its lock. This
function does not make an agent-submitted source capture or metadata trustworthy,
issue a training completion, or replace checks on the actual launched model.

## Fixed source for native invocation

`native_training_metadata` resolves model configuration in a separate confined
process from the captured JSON and selected source. It uses the native plugin
schema and Model-I/O cardinality authority, returns validated effective settings,
and does not instantiate a model or optimizer. Candidate stdout is kept off the
JSON reply channel. The same source-binding implementation is used by epoch
model restoration, including finite packages. Run this once before launch,
without private data or credentials; its response is not caller authorization.

The inherited client resolves native `device="cuda"` to this process's current
CUDA index before sending metadata and RNG. Explicit indices remain explicit;
do not assume an omitted index means device zero. The operator must preserve
the same CUDA device mapping between training and numerical workers.

`native_training_inputs.capture_native_training_inputs` uses the actual native
argument parser, reads effective inputs below operator-selected public or
research roots, and saves exact bytes in a unique protected directory. It appends
canonical captured paths to the native command, preserving existing repeated,
abbreviated and equals-form option semantics. Parallel invocations get separate
captures. Invalid inputs or paths escaping the allowed roots refuse before
publishing a capture. Mount captured files read-only into training children.
Task scope payloads remain opaque bytes: a task need not serialize scopes as
JSON. Their existing native digest/decoder contract remains responsible for
validation; only native configuration JSON files are JSON-decoded during capture.

Task manifests retain their original paths because their declarations may be
relative to the manifest location; the protected launcher must admit that path
separately. The capture does not approve data/output paths, authenticate callers,
or approve plugins. Both native builtin/custom history tests deliberately corrupt
the original model configuration after capture and still complete two epochs
using captured inputs. Frozen task/evaluation packages are not rewritten.

The TIDMAD deployment adapter
`experiments.tidmad.main_orchestrator.validation_scope.admit_validation_scope`
checks captured scope against the operator's profile/band and the resolved model
segmentation. It reuses the task decoder, native range validator and public row
declaration, without opening data. Omitted embedded profile retains the native
bound-profile behavior; use that same operator profile during materialization.
Other tasks supply their own scope adapter; generic transport does not inspect
TIDMAD fields or impose its scope format. Caller/source/Unix admission still
belongs to the protected deployment entrypoint.

`validation_code_snapshot.stage_validation_code` consumes a framework
`CapturedCodePackage` and copies its already-captured bytes under a protected
operator parent. It reuses the framework's package identity/capture checks,
keeps relative Python member paths, imports no candidate code, and never rereads
the mutable research source. Each call creates a separate directory; malformed
or inconsistent captures fail before use. Worker-readable source files and
directories are non-writable, with access to the enclosing parent controlled by
the deployment. Mount only the selected directory read-only into workers.

Use the returned capture for review inputs and the actual native source path.
Staging does not by itself redirect imports or confer training authority. The
native custom-loss regression deliberately invalidates the original research
file after capture and then trains/validates using the staged copy. The epoch
model worker also exercises a two-file relative-import plugin in a real child:
changes to the original research helper do not affect the staged model, while
changes to the staged helper refuse before import. This establishes packaged
model reconstruction; it does not establish packaged custom-loss review.

## Native process confinement smoke

Short synthetic replay also exercises actual native training plus model/loss
workers in separate filesystem, PID and network namespaces. Validation files
are hidden from every child; only the coordinator can materialize them. Both
builtin and reviewed synthetic custom objectives complete two epochs and retain
native history. This is evidence for the execution connection and mount layout,
not for caller authentication, different Unix identities or installed H100 service.

When a worker namespace omits the host passwd database, configure writable
`TORCHINDUCTOR_CACHE_DIR`, `TRITON_CACHE_DIR` and `CUDA_CACHE_PATH` inside its
own temporary filesystem. PyTorch may initialize its cache while constructing
an optimizer even without explicit compilation; relying on username lookup can
fail before training starts. Cache paths and mounts are deployment inputs, not
changes to the frozen task or training configuration.

### Captured native configuration and epoch allowance

The protected launcher builds the configuration probe with
`native_training_metadata.captured_configuration_request`, using its own captured
inputs and admitted model source. The reader verifies captured paths and hashes;
the candidate configuration class is resolved later inside the confined probe.
The returned epoch ceiling follows native behavior: the training-budget envelope
wins when a runtime observation output activates that policy; otherwise the
training configuration's proposed epoch count applies. Do not clamp this ceiling
back to the proposed count. Native training retains time/step admission and early
termination. The private validation service merely accepts epochs authorized by
that same invocation; this helper adds no workflow budget or training-pool limit.

### Native optimizer-step evidence

`AdmittedValidationWorkload.optimizer_steps_per_epoch` is an optional exact
cross-check for deployments with an authoritative fixed count. Omit it for
native jobs whose task sampling/materialization determines the count. The
native engine rejects zero-step epochs, owns drop-last and training budgets,
and reports the actual completed step count. The service still checks full
configuration/scope identity, positive completion facts, epoch sequence and
the admitted epoch ceiling. Neither an exact count nor completion metadata is
proof of honest optimization: provenance comes from the protected launch and
its inherited channel, with the limitations described above. Do not add a
second dataset materialization solely to guess a service-side step count.

## Explicit Linux namespace layout

`validation_confinement.ValidationNamespace.prefix()` renders the bubblewrap
prefix accepted by native-training and numeric-worker launchers. Protected
operator configuration selects absolute read/write/device mounts, working
directory and optional UID/GID. No host filesystem is mounted by default.
Each child gets separate PID, IPC and mount namespaces, drops capabilities and
uses private temporary caches. Networking is isolated unless the operator
explicitly preserves it for native training; numeric validation workers must
keep it isolated. This does not change the outer coding agent's permissions.

Supply only required runtime/source/state mounts to workers. Private datasets,
coordinator credentials and unrelated processes must remain outside their
visibility. `hidden_directories` can mask a private subtree of a mounted test
fixture; production should prefer mounting only the required public paths.
Writable mounts, identities, device/library bindings and the outer run cgroup
remain deployment decisions, not researcher input. The builder neither checks
caller authorization nor installs services. Before changing UID/GID, provision
read/traverse permissions for required immutable worker inputs and explicitly
writable outputs; do not make private coordinator directories public to fix
permission errors.

Worker launch passes a read-only config descriptor alongside the numeric state
descriptor. Config and stderr diagnostics stay owner-only (`0600`); the worker
need not see their host directory. All three worker CLIs retain `--config` for
existing callers and also accept `--config-fd`, with the same bounded JSON read.
This avoids opening coordinator directory permissions when selecting a separate
worker UID. Reviewed-objective bundles and model package files still require
explicit, narrowly scoped readable mounts; the config descriptor does not grant
access to those paths.

## Confined admission probes

`validation_admission_process.AdmissionProbeRuntime` supplies the actual
configuration, objective-metadata and numerical-review subprocess calls. Bind
its Python, environment, namespace mounts, private diagnostic parent and one
continuing monotonic deadline from protected deployment settings. Numerical
review plugs directly into `review_native_objective_once` as `runtime.numerical`.
Keep private datasets and diagnostics outside probe mounts; networking is
required to be isolated. The separate purpose-review gateway remains responsible
for its explicitly configured provider and review evidence.

Each probe records stdout, stderr and elapsed/status evidence in its own private
directory, validates bounded output with the corresponding schema, and kills a
probe that exceeds the remaining deadline. Later probes cannot reset that
budget. These probes run at admission, never in per-epoch validation. The native
integration test uses actual confined metadata and numerical review; its purpose
verdict is synthetic and is not evidence for a live model-service review.

## Bind admitted model source to native training

`run_admitted_native_training(..., model_source=...)` forwards the operator's
`EpochModelSource` to `native_training_entry` using an inherited read-only
source descriptor. The entry validates its schema and hashes, binds the same
builtin/single-file/staged-package source mechanism used by validation workers,
and retains that binding through native training. Pass the identical source
selection to configuration admission and epoch model reconstruction. No candidate
plugin is imported by the private coordinator to discover its configuration.

This optional transport is accepted only with the deployment's native entry
module. Existing calls without it retain their entry behavior. Source binding
is not caller authentication: the protected launcher still captures and admits
sources and controls the child environment/mounts. A real two-epoch synthetic
custom regressor exercises the admitted-source native path alongside builtin,
custom-objective and native-budget cases.

For the TIDMAD deployment, `validation_scope.admit_captured_validation_scope`
connects the operator-created native capture to the frozen manifest path/hash,
task adapter id, optional captured profile and digest-verified validation scope.
It then applies the existing profile/band/geometry checks and row declaration.
The launcher must protect the manifest and referenced task files for the whole
job and bind the same profile during private materialization. This checks the
validation selection without changing training pools or frozen task bytes;
other tasks provide their own scope-admission adapter.

Pass the invocation's same monotonic `deadline` to
`review_native_objective_once`. Both its per-objective cache lock and the short
publication lock then stop waiting when that deadline expires. Contention must
not silently extend the job budget or trigger duplicate review. The deadline is
not part of review identity, so a later authorized job can still reuse completed
matching evidence. Numerical and provider calls retain their own execution
cancellation responsibilities; the lock timeout does not interrupt those calls.

`AdmissionProbeRuntime.model_selection` runs `native_model_discovery` in a fresh
confined process using the operator-staged plugin roots/package transport in
its environment. It observes the installed native registry and declaration
origin; it does not duplicate directory scan or precedence rules. The operator
then calls `validation_code_snapshot.bind_discovered_model_source` to match the
selection against its staged package and installed constructor/builtin hashes.
This binding performs no candidate import and never opens a probe-selected
path: a plugin must name an existing captured member with the recorded digest.
Use the resulting source for both configuration admission and native training.
The two-epoch native integration covers builtin and staged custom models; the
original research plugin is deliberately changed after capture.

### Per-invocation custom loss transport

For an approved native loss, call
`native_loss_binding.admitted_loss_source` with the protected review bundle and
expected policy/objective identities. Pass its result as `loss_source` to
`run_admitted_native_training`. The channel passes source and effective defaults
through a read-only inherited descriptor; it does not expose review evidence or
private targets to the training child. The confined native entry registers that
source through the existing loss registry and checks its native defaults against
the reviewed parameters before training. Private validation reconstructs the
same reviewed source and applies the native epoch's numeric criterion state.

This is an invocation binding, not a run-wide loss policy. A later invocation
can use a new loss or a new version with the same name. Parallel native children
have independent registries and can use different versions simultaneously.
Unchanged reviewed material uses the existing review cache; no review runs each
epoch. The optional binding changes neither callers that omit it nor fixed
workflow execution. The native loader remains responsible for plugin semantics.

For multi-file losses, supply `ObjectiveCodePackage(entrypoint, sources)` on the
metadata and numerical requests. Every file must be a normalized finite Python
member accepted by the existing framework package declaration. The entrypoint
bytes must equal `source`, and the package files must equal the complete reviewed
material. Metadata records the package digest; review admission matches it to
numerical execution. Changing a helper changes review/cache identity too.

The metadata probe, numerical probe, training binding and private objective
worker all use `bound_objective_source`, which stages supplied bytes and reuses
native `capture_package` / `bind_code_package`. Relative and delayed imports
therefore use captured members. Source inspection checks every helper and permits
relative imports only to supplied members. The numerical checks retain native
pair, scalar and gradient semantics. Two-epoch integration covers classification
and a custom regression model with multi-file losses; purpose-review decisions
in these tests remain synthetic, not live-model qualification.

This transport does not establish caller authentication or prove that every
native agent route has been installed. The operator must derive the review from
the native-selected artifact and protect the process environment and source
lifetime before invoking this interface.

### Assemble the admitted native job

After caller and source admission, call `native_job_admission.admit_native_job`
with the captured native inputs, selected model source, confined configuration
probe and a task-owned scope callback. It resolves the native model configuration,
loss routing, batch size and activated epoch budget, then constructs the common
validation workload. It does not guess optimizer steps or change training pools.
The task callback owns scope semantics; the generic assembler imports no task.

Custom jobs also receive the operator's `NativeReviewedObjective`. Assembly
matches review material and defaults against the selected native loss, verifies
the protected saved bundle, and derives worker target dtype from native objective
metadata. The returned model/loss sources are passed to native training; the
returned plan is passed to `AdmittedEpochExecutor`. A manually populated worker
dtype must not override the actual plugin declaration. Review is reused here,
not called again. Six synthetic two-epoch integration cases exercise this path.

This helper connects admission components; it is not a research-facing service
or caller authentication layer. The installed entry must still supply protected
paths, environment, UID, continuing deadline and the actual source capture.

### Per-invocation privileged entry

`deployments/shared/native_training_entry.py` bootstraps from an immutable
experiment checkout using that checkout's exact interpreter with `-I -B`.
An operator-installed wrapper must fix the script and policy path before
appending the native command. Grant sudo only to that fixed wrapper; do not
allow arbitrary Python commands or caller-selected policy paths. The wrapper
must preserve the original working directory until dispatch captures it.

`native_launcher.dispatch_native_training` reads a bounded, operator-owned
policy, verifies sudo-issued UID/GID against the assigned run account, and
converts the existing absolute run deadline to a continuing monotonic deadline.
It discards inherited coordinator environment variables, changes to the protected
policy cwd and calls only the policy-selected handler. It never executes the
research command itself. Native arguments and original cwd remain untrusted;
the handler owns source/input capture, task admission, model/loss review,
namespace/UID selection, execution and complete process-group cleanup.

The current tests establish caller refusal, policy permissions, deadline
preservation and real child-process dispatch/environment replacement. They do
not establish an installed sudo transition or a completed task handler. Do not
install/grant this wrapper until the configured task handler is implemented and
qualified. Fixed workflow and the existing baseline scorer are unchanged.

`AdmissionProbeRuntime.loss_selection` runs native name lookup in a confined
fresh process with operator-staged loss directories and an optional finite
package declaration. It returns the selected declaration path and source hash;
it does not construct the criterion. `bind_discovered_loss_package` matches that
observation to the operator's captured members without opening a returned path
or importing candidate code. Pass the resulting exact package to objective
metadata/review. Directory precedence remains owned by the native loss loader.

The launcher context retains only the native source/workspace locator keys
(`SIDERIUS_PLUGIN_DIRS`, `SIDERIUS_LOSS_DIRS`, generated-library/workspace and
finite task-code manifest/digest keys) as **untrusted data**, before replacing
its coordinator environment. A deployed sudo rule must preserve those explicit
keys if that route uses them; never preserve arbitrary research environment or
provider secrets. They do not become mounts or authorize source reads.

`native_source_capture.capture_selected_source` matches a confined probe's
selection to a bounded descriptor read under operator-authorized readable roots.
`capture_selected_objective_package` captures only declared Python members,
including helpers, using the same path reader. Neither imports source or scans
unrelated files. A changed selected file, escaping path or symlink is refused.
This is source capture for the task handler, not a standalone launch endpoint.

### Concrete task handler

`experiments.tidmad.main_orchestrator.native_handler:run` is a concrete handler
for `NativeLauncherPolicy`. Its settings validate as `TidmadNativePolicy`: generic
`NativeRuntimePolicy` holds interpreter, entrypoint, readable roots, namespaces,
child environment, installed implementation identities and transport limits;
the task layer supplies the frozen manifest identity, its explicit
`task_data_path_id`, profile, permitted band scope and private validation location.
Use the ID from that selected composition (for example
`tidmad_frozen_training_pool`); do not substitute a generic `tidmad` ID. Optional `NativeReviewPolicy` declares
protected review cache, provider configuration, credential file and task-owned
synthetic fixtures. Credentials are used only by the existing `LLMBridge`, never
passed to training or numeric workers.

The handler captures native inputs and an inherited finite code transport,
observes native model selection, binds captured source, resolves native
configuration and validates task scope. Only then does a custom loss enter native
selection and automatic review. It assembles the admitted workload, adds narrow
read-only capture/bundle mounts, runs native training with separate numeric
workers and saves a private execution receipt containing stage/epoch timings.
The review cache is used once per objective identity; there is no epoch review.

Inherited package transport uses the framework's `CodeTransport` schema, with
its carrier and every pinned member read through the deployment's allowed-root
bounded descriptor reader. Single files retain their separate capture route.
Research locator environment enters only confined discovery probes. Native
training receives the admitted model/loss bindings instead of those mutable
source directories.

Synthetic two-epoch tests now execute this handler for builtin, single-file and
multi-file custom losses, including inherited package transport and namespace
mounts. They inject a synthetic semantic-review verdict. Installed sudo,
different host Unix identities, live provider credentials, H100 execution and
the baseline-equivalent namespace/mount policy still require deployment
qualification; these tests do not establish those properties. The operator must
provision protected job/cache parents and exact policy mounts/UIDs before install.

### Host-identity deployment requirements

An explicit namespace UID means an actual host account. The coordinator must be
root and the runtime must provide `/usr/bin/setpriv` and bubblewrap with
`--perms`. Namespace setup retains the host user namespace, then drops the host
UID/GID, supplementary groups, capability sets and privilege escalation before
candidate execution. A bubblewrap `--uid` inside a one-ID user namespace does
not establish that boundary. Verify host ownership of created files and denial
of root-owned private files, not only `getuid()`.

Mount only the required runtime, public task inputs and research workspaces.
Synthetic intermediate mount directories must be traversable; namespace-local
`/tmp` must permit the selected account to create runtime caches. Neither rule
requires mounting or changing permissions on host private parent directories.
Keep private job/cache/validation roots outside public workspace mounts.

For inherited multi-file code, discovery needs read access to the code transport
manifest as well as its declared source members. A public manifest produced by
the research account must remain readable by that account in the probe. Preserve
only the documented locator environment keys across the fixed sudo wrapper;
these keys alone do not authorize additional mounts. Qualify single-file and
multi-file requests separately using the installed runtime and actual accounts.

### Public trained-model reconstruction evidence

The native child initially records the captured model configuration, selected
model source and training-scope paths it actually used. Those capture paths can
be inaccessible outside its namespace. Before the deployment training entry
returns, `native_training_provenance` verifies their observed hashes and retains
exact copies under the public result directory's `training_provenance` folder.
It updates only the typed sidecar's paths; checkpoint, source/config/scope hashes,
sizes, model identity and effective loss remain unchanged. The native parent
then performs its original artifact certification against those readable bytes.

This publication runs as the research training UID inside the target-free
namespace. It does not expose private job directories, validation data or
coordinator receipts, and does not duplicate checkpoint weights. A changed
source fails publication instead of changing its declared identity. Ordinary
framework/workflow training without this deployment entry keeps its existing
sidecar behavior and filenames.
