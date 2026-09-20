# Research-side scripted model export

`qualify_scripted_model` detects unsupported scripting, output differences on
explicit caller examples, and parameter/buffer mutation. Call it before training
and again when exporting restored trained weights. `export_scripted_model` writes
`model.pt`, `weights.pth` and an export receipt into a new directory, then checks
the saved model's state and example outputs. It never silently falls back to
tracing. Existing destinations are refused.

Pass a disposable CPU model in evaluation mode and examples that cover the
declared task shapes. This runs model code: the research process must provide
the same filesystem, resource and deadline isolation as training. The helper
itself creates no sandbox, imports no task and reads no dataset or credentials.
Rejected stateful models can mutate their disposable in-memory instance during
qualification. Do not pass a live training model.

This is a serialization component, not a complete native-candidate adapter.
The caller still owns certified artifact/config/source reconstruction, metadata
and source packaging, the scientific input/output contract, resource limits,
submission and full evaluator replay. Example parity is bounded evidence, not
a proof of equivalence on every possible input or scientific validity.

## Explicit tracing

Both functions accept `method="script"` (the unchanged default) or an explicit
`method="trace"`. Tracing can export native models whose constant configuration
branches are not accepted by the script compiler, such as the existing FCNet
regression head. No automatic fallback changes the selected method.

Trace export requires at least two caller-provided comparison examples and runs
PyTorch's graph checks against the additional examples. The common native/output
parity and state checks still run, including after serialization. The export
receipt records `serialization_method`. Include different batch sizes and input
values representative of the declared evaluator inputs. A graph disagreement or
observed state mutation fails before publishing the candidate.

Tracing cannot prove behavior on untested data-dependent branches. Its receipt
is bounded serialization evidence, not proof of equivalence for every input.
The frozen evaluator and its candidate contract are unchanged.


## Native checkpoint reconstruction

`native_model_export.export_native_model` supplies the shared research-side
reconstruction step. It consumes the framework's `CandidateEvaluationRequest`,
uses the already-bound native model/config registries, exact attempt checkpoint,
effective loss configuration and model I/O contract, then applies the existing
cardinality/constructor/input-dtype owners. Task callers provide comparison
examples, serialization method and their evaluator metadata/acceptance checks.
No scientific task or candidate layout is selected by this shared helper.

The helper retains checkpoint/configuration and source-hash evidence for
observation. It is not privileged training certification. As with model export,
run constructors and forwards only in the research boundary; bind the same
registry as the training invocation. Historical inference's separate single-file
plugin/sidecar requirements do not apply to this path.

## Deployment device qualification

`qualify_scripted_model` and `export_scripted_model` accept optional
`execution_devices`. For each explicit device they load a serialized copy on CPU,
move it to that device, compare against an eager copy on the same device and
check state preservation. This catches traces with device constants that pass
CPU tests but fail GPU inference. The original caller model stays on CPU.
No devices are guessed; the default preserves the existing CPU-only behavior.
The export receipt records the checked devices. This tests supplied examples,
not all possible inputs or future configurations. Use the same checker before
training and after loading the trained weights.
