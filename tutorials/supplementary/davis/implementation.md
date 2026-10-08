# DAVIS tutorial ownership and validation

## Task and experiment boundary

The tutorial consumes `tasks/davis_future_prediction/compositions/bounded_qualification.yaml`
without altering its original scientific declarations. Its selected manifests
contain one first-window clip per sequence: 60 Train and 15 Validation. The
15 Final sequences remain declared evidence but unbound to execution. Native
scope selection owns rounding and seed behavior. The original exact-L1 objective,
MSE/lower primary, PSNR/higher and MAE/lower secondaries, model I/O and blocking
Health dispersion floor remain unchanged. Historical qualification launchers,
source pins, lockfiles and paper artifacts are outside this change.

`DavisExperiment` owns absolute external paths, four clip-scope fractions in
[0.01,1], iterations, rounds, epoch ceilings and positive time/VRAM allowances.
Defaults: 3 iterations, 2 rounds, 1 epoch, Trial Train 0.25 and Validation 1,
Formal Train 0.5 and Validation 1, training allowances 2/5 minutes and VRAM 10 GiB.
Phase VRAM overrides follow the existing shared hardware contract. No historical
32 GiB host address-space override, watchdog disable or hardware whitelist is added.

`project` copies the task, selected workflow, notebook and all-Luna configuration
into a fresh external project. It creates exclusive JSON/script pairs and clears
notebook outputs. `save_variant` creates fresh run identity without overwriting
prior inputs/results. Shared `saved_script` validates literal launcher bindings.
`runner` uses native `run_chain.sh`, operator Formal scope, structured regressor
output, snapshot scope selection and fixed `train_portion=1` for both phases.
Scope flags own clip fractions; the task explicitly refuses fractional epochs.
Data Analysis, literature review and human advice are disabled. Health remains
blocking and result authority remains diagnostic; no Health PASS is promised.

## Data and composed-module identity

`data` verifies copied original manifests, execution probes, decoder bytes and
Health declaration against the repository authority. It checks required Train/
Validation frames and the pinned archive's presence. It uses the already composed
task module for manifest parsing, frame paths, probe decoding and dataset preview.
A second normal-package decoder import would register another module identity;
the adapter must not do that or bypass the native registry.

`selected_task` checks original manifest references, native task id, objective,
metric and the currently saved ForwardContract using native model validation.
It compares against the original task declaration, not duplicated tensor literals.
The existing `assert_cached_task_config_source` rejects edited task configuration
in the same notebook process. Restarting the kernel allows changed descriptive
text; a changed tensor contract is refused even in a fresh process. No native
cache is cleared or changed. This respects the loader's frozen process lifecycle.

Ordinary review checks frozen manifest identity and nonempty frame presence.
Fresh launch additionally hashes the official archive and checks ten existing
frozen decoded-window probes. The archive hash does not establish equality of
all extracted frames, and probes establish only their named windows. The tutorial
does not claim full extracted-dataset cryptographic verification. `input_digest`
binds all copied task files, saved JSON/script/workflow/routing, checkout identity
and every Train/Validation window frame's resolved path/size/mtime. This detects
ordinary replacement, not hostile same-metadata modification or concurrent races.
Final frames are not decoded by preview/training/scoring.

## Effects, readiness and presentation

`demo` delegates execution, reuse and failed-process cleanup to shared `saved_run`.
It invokes the saved script; it owns no alternate trainer or LLM gateway. Keys
are checked before launch effects. Shared GPU checks use the exact selected infra
environment, current occupancy, quota and configured allowances. Passing is a
snapshot, not reservation/model-fit proof. RAM/disk reporting is observational;
no unmeasured universal minimum or maximum is claimed. Notebook timeout and
native phase allowances are not whole-run provider billing limits.

Score plotting reads native Formal records through shared `progress`, requires
MSE/lower and preserves task Health evidence. Failed scored points are hollow;
unscored outcomes are not zeros. Plotting an existing run requires no dataset,
keys, GPU or launch. No extra plot semantics, alternate metric or no-Health
shortcut is introduced. The public example retains the executed source pair
and actual evidence; initialization clears archived outputs for new users.

## Direct acquisition repair

Only `fetch_davis.main` root and manifest resolution change: the repository root
is the tool's `parents[3]`, and layout validation reads the task's current
`data/manifests/sequences.csv`. The corrected out-of-tree guard runs before fetch.
Archive retrieval/extraction mechanics and pins are unchanged. Owning data docs
use module invocation. Adjacent acquisition tools and manifest generators are
outside this PR; no historical manifest is regenerated.

## Focused verification and qualification boundary

Tests exercise native CLI parsing/normalization, real composed clip selection
and decoder shapes, repeated same-process composition, scope/epoch distinctions,
wrong forward contracts and stale cache refusal, original data identities,
archive/probe failure, credentials before GPU, saved variants/output clearing,
completion reuse and Health-aware MSE plotting. Acquisition tests isolate the
owning tool process, prohibit download and prove root refusal/current 90-sequence
manifest reachability. Existing task-package checks cover scientific bindings,
pins, disjointness and historical qualification commands.

Real CPU checks reuse the existing official dataset, verify archive SHA-256 and ten
probes, inspect 900 required Train/Validation frames, and display all 8 context and
4 target frames through the native dataset. Final committed saved-script preview,
all three rendered native argv normalizations and a copied notebook with live
execution disabled are separate checks.

## Recorded live witness

The example records exp `a06096a19de7362f5ffadbab7da3f194c444983d` with infra
`52373be9a52bead36fd1f15d706385967e0a129d`. Three iterations ran with all-Luna
routing and the declared defaults. All first implementations passed validation.
Iteration 1 retained two scored `failed_mode_collapse` outcomes; its manifest
status is `no_records`. Iterations 2 and 3 passed Health and have `completed`
manifests. All result authority remains diagnostic. The gallery preserves the
first hollow point and does not equate script completion with scientific validity.

Saved native TrialConfig/task_scope establish 15 Trial and 30 Formal clips,
with all 15 Validation clips in each phase. Native `drop_last=true` may omit a
partial final batch; selected scope is not an assertion that every selected
row contributed an optimizer step. Saved native TrialConfig/task_scope own
actual selected data; reflector prose is not an execution receipt.

The authorized run made 31 settled requests, accounted at $0.048500750.
Full notebook command time was 756.000064 seconds; cached reuse took 5.114115
seconds, made no new requests and preserved the completion receipt. The
provider remained available during reuse. These are observations, not public
notebook spending limits or measured GPU utilization. No score-driven rerun or
manual model repair occurred.

`example/provenance.json` allowlists settings, data identity, native statuses,
Health evidence, timing and hashes. PNG/SVG bytes come from the actual executed
notebook/plot. CSV numbers remain unchanged; source paths become project-relative.
The notebook embeds image-only outputs in its data and score cells, with no raw
console, request, response, credential or machine-path outputs. Original
scientific declarations and all operative notebook code remain unchanged.
