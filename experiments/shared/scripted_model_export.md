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
