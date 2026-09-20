# Native implementation export gate

`implement_for_scripted_export` invokes a caller-supplied native Implementor
through its typed `run(ImplementorInput) -> ImplementorOutput` interface. The
caller configures the native LLM gateway; this adapter constructs no provider.

It adds the deployment's TorchScript submission requirement to a copied task
description. Scientific human advice and expert advice are preserved, including
absence in NoPrior. It does not edit the frozen task package or scientific
architecture, portion, training budget or epoch policy.

Before returning, it checks candidate/model identity, applies only the native
output's validated config adjustments whose original values match the proposal,
and constructs that concrete config using the native loss-aware constructor.
A source snapshot remains present during scripting. Explicit CPU input examples
must be supplied by the caller from the task's declared contract; no sequence
length, task, hardware model or batch size is hardcoded here.

`ImplementationExportError` contains a bounded repair diagnostic suitable for a
subsequent native call's `previous_validation_failure`. The caller owns retry
count, deadline and resource limits. The adapter does not invoke training or
replace the native code validator. The typed result binds source digest, selected
config, loss and example count; it is serialization evidence only. Tuner config
changes invalidate this concrete qualification and need rechecking. Trained
weights still require the final certified exporter and evaluator replay.

Run only in a fresh isolated research worker without private data authority.
Generated source is executable; this helper supplies no filesystem or process
isolation. Complete orchestration dispatch and enforced handoff to training are
not provided by this component. The current test invokes the adapter with a
controlled Implementor implementation and real plugin construction/scripting,
not an external LLM or scientific training job.

## Explicit method and deployment devices

The default method remains `script`. An explicit `method="trace"` requires at
least two CPU comparison examples and sends that chosen format to the native
implementor. `execution_devices` names the actual deployment devices; each is
checked by CPU-loading the serialized model and moving an isolated copy there.
The default empty tuple preserves the original CPU-only qualification. The
result records the selected method and checked devices. Device checks use small
caller examples, perform no optimization, and require no extra model request.
See the deployment submission guide for required devices and input contract.
