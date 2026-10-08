# Pet tutorial contract

Ownership: task science remains in the copied `tasks/oxford_iiit_pet` package;
experiment choices are `PetExperiment` plus the explicit external fixed-workflow
JSON. `runner.build_command` is the sole mapping from exposed knobs to native
flags. Its overrides take precedence over corresponding workflow values.
Historical `two_iteration_qualification` remains unchanged.

`project.create_project` refuses any existing destination or nesting with source
checkouts/images. User inputs and execution workspaces remain external. Generated
scripts bind the exact exp interpreter, read the saved experiment every invocation,
and route execution to the public native chain. Preview performs no provider call
or GPU allocation. Launch additionally decodes search images, checks exported key
names and uses the [shared GPU setup adapter](../../shared/gpu-runtime.md).
Source/dependency pins and planner identities must match.

`data` resolves explicit manifests without training-as-evaluation fallback. It
rejects duplicate/overlapping IDs, missing classes, inconsistent role/class labels
and paths outside the task package. `resplit_task` creates a new package from the
train+validation pool only, updates composition/profile, and preserves final bytes.
It does not mutate the frozen historical split algorithm.

Pet uses `native-timing-v1`, fixed workflow, disabled DA/literature/advice, diagnostic
result authority and blocking Health. The initial three iterations/two rounds/
32 epochs and role budgets are experiment settings. Epoch thinning stays 1.0;
Pet's runtime refuses smaller values. Invalid Health is not demo failure by itself.
A missing score is never fabricated.

`demo.run_demo` delegates to the saved script with a separate process group. Its
completion receipt binds experiment, script, routing, workflow and all task files;
changed inputs cannot reuse a completed result. This is input provenance, not a
content hash of the external JPEG dataset. The operator must preserve dataset
contents. Timeouts/interruptions stop the process group and retain the log.
The notebook's wall timeout is not a billing or GPU-accounting implementation.

Shared environment/strategy/bootstrap/progress helpers own generic mechanics.
The old paper import paths remain compatible. No Pet branch is added to the paper
experiment schema, preflight dispatch or quick-demo dispatcher.

Validation owners: deterministic tests cover native argument propagation, task
split isolation, missing/overlapping inputs and output alias refusal. Offline
notebook execution covers saved-file review and delegation setup. A bounded real
three-iteration qualification must establish actual generated-model execution,
recorded scoring/Health transport and visual output before claiming real completion.


## Saved experiment handoff

The notebook requires `TUTORIAL_HOME/project.json` and the bound exp kernel,
independent of cwd. README setup registers the kernel externally and opens
Jupyter at the project root. Default Run All reloads `SELECTED_EXPERIMENT` and
never overlays tutorial literals onto its saved JSON.

`project.save_variant` validates the selected external JSON with `PetExperiment`,
merges explicit changes and assigns the same fresh name to experiment/script/run
paths. It refuses existing JSON, script or workspace. Originals remain untouched;
I/O failure may leave a partial new pair requiring a new name or manual inspection.
Saving is opt-in. After saving once, disable the switch and select that saved
name for subsequent notebook passes. The optional resplit retains its existing
seed/stratification/final preservation and saves its changed composition through
this separate-pair handoff rather than replacing the parent experiment.

`project.validate_launcher` checks exactly one literal absolute `EXPERIMENT` and
`EXP_CHECKOUT` assignment plus the generated Pet runner exec line. Both saved-file
review and `run_demo` call it before data inspection or execution/reuse effects.
It catches mismatched saved inputs; it is not a parser or safety certificate for
arbitrary shell code. Execution still belongs to the saved script and existing
runner. Pet's existing cache and timeout semantics are unchanged.

`PLOT_EXPERIMENT` and `PLOT_OUTPUT` select saved results independently of the live
launch flag. Only the plotting cell needs to execute to replot an existing run;
it reads the saved workspace and native score records, with no launch/preflight.
`RUN_NATIVE_PREVIEW=False` disables the notebook's native preview for an explicitly
offline file walkthrough; it does not disable saved-launcher checks on real runs.
The source notebook's archived outputs and separate gallery retain their original
provenance. Initialized copies still clear all code outputs.
