# Prepared workflow demo contract

Scope: Project8 dual representation and LIGO, diagnostic three-iteration
NoPrior fixed-workflow demos. This entrypoint does not reconstruct paper
artifacts, enforce model quality, run a final test or launch campaign clocks.
Scientific source task packages and their experiment defaults are unchanged.

## Owners and interfaces

- `project.py` initializes one fresh external project and copies its notebook,
  task adapter code, provider routing and literature settings. It saves typed
  `PreparedExperiment` JSON and an explicit Bash launcher. Existing files and
  configurations with changed settings under an existing name are refused.
- `data.py` owns `DatasetRecipe`, bounded source selection, prepared arrays,
  split identities and the matching copied task declaration. It reuses
  `PreparedDeclaration` and the native array layout. User requests change only
  their external project. A fresh dataset name is mandatory; neither source
  inputs nor prior task/data pairs are overwritten.
- `http_ranges.py` is seekable HDF5 transport, not preprocessing. Each block is
  at most 1 MiB; the in-memory LRU retains at most 32 blocks. It requires HTTP
  206, exact Content-Range and exact payload size. It never accepts a server's
  full-file fallback. URLs are pinned by `sources.json`; credentials are not
  sent to the data service. Whole raw-file LFS digests are provenance only:
  partial reads cannot verify them.
- `runner.py` validates the saved experiment, renders the existing workflow
  and treatment, performs shared source-pin/installed-version/CUDA/key checks,
  verifies all five small prepared-array hashes with the native verifier, and
  delegates to `scripts/launch/run_chain.sh`. It never invokes a provider
  directly. Literature Review stays enabled, advice and Data Analysis disabled.
- `review.py` reopens saved files, verifies exact launcher bindings and prints
  actual paths, budgets, fractions, populations and commands. Presence review
  is not native launch validation or API authentication.
- The shared `quick_demo.py` invokes the saved shell script, owns its process
  group and completion receipt, and reuses recorded runs. Notebook cells own
  explanation, configuration editing and explicit script invocation only.

## Data and split semantics

Default 512 training / 1,000 validation events, with a fixed 100-event epoch-loss
snapshot. Trial fractions default to 0.5/0.5 and Formal to 1/1 within these small
populations. Formal training scope is explicitly operator-owned and per-epoch
exposure is 1.0. Both stages use full per-epoch exposure and an experiment-fixed batch size of one to provide enough real timing observations. Scoring fractions
do not change the fixed 10% training-validation loss snapshot.

The source subset is the first selected rows in original prepared ordering:
Project8's first training/validation shards, and LIGO's first SNR 10–15 shards.
No test file enters either route. Local input requires the original manifest
pinned by the existing time-domain prepared declaration, plus exact array
shape/dtype checks. Only selected values are copied and hashed; this is not a
full-source checksum qualification. Downloaded rows use the same preprocessing
as existing prepared data. Live transport parity is validated separately.

Project8 reuses `dual_representation()` to add full orthonormal complex FFT
real/imaginary channels to normalized time I/Q. It binds
`Project8DualRepresentationDataPath`, preserves the four-channel forward
contract and requires both views to contribute. The native schema does not
prove representation use; generated model source and input sensitivity must
be inspected as separate evidence, with saturated/dead models inconclusive.
LIGO retains the 15104:16128 whitened detector crop and physical targets.

An optional re-split pools only the selected demo train/validation observations,
uses a seeded permutation and preserves original split:row identities. Validation
count is floored to a multiple of ten with a twenty-row minimum. A fresh
manifest, fixed loss subset, prepared declaration, dataset profile and task text
are generated together. Re-splitting the small local demo does not fetch data
again or apply Project8's FFT twice. Validation feedback is not unseen testing.

All five output arrays are read-only and fully hashed before launch. Read-only
files are accidental-edit protection, not a sandbox for generated Python. The
native fixed workflow executes as the current non-root account.

## Plotting and validity

The unchanged paper plot style is shared. Default `health_policy="required"`
retains TESS/TIDMAD semantics: missing Health results are unknown.
`review.plot_demo` checks the selected composition has exactly
`task_health: {none: true}` before opting into `health_policy="none"`. Successful
finite scored records then have filled markers; failed scored records remain
hollow. This means successful execution under an explicit no-Health task, not
Health PASS or scientific certification. Missing metrics remain absent. CSV
retains raw values and record paths; negative R2 uses the existing boundary
triangles. Plotting never calls a provider or trains.

## Validation scope

Focused regression tests cover changed task/data identities, no overlapping row
membership, preserved source bytes, no repeated FFT on a re-split, explicit
Formal scope and dual workflow parameter rules, exact HTTP random access,
rejection of full-file download fallbacks, and absent-vs-disabled Health checks.
Existing TESS/TIDMAD tests remain regression requirements. Live notebooks and
real source range parity are reported with actual outcomes in the PR; a passing
unit suite alone does not establish a completed autonomous search.

## Small data still needs enough batches

The default uses 512 training events, batch size 1 and full per-epoch exposure
inside the selected scope. A 50% Trial has 256 batches per epoch. The 1,000-event
validation pool fixes 100 events for epoch-loss monitoring; four epochs provide
up to 400 validation observations. These counts give the native runtime verifier
more real observations; it still decides whether timings are stable enough.

The large validation-to-training ratio serves timing measurement in this short
demo, not a recommended scientific split. Reducing data or fractions, increasing
batch size, or reducing epochs can leave too little evidence and cause rejection
before scoring. A custom 64/20 dataset is for offline file-editing practice.

Project8 retains a partial final training batch. LIGO keeps native `drop_last`
behavior, which can discard a partial tail after a custom batch-size change;
batch size 1 has no partial tail. No Health threshold, training allowance or
runtime verification rule is relaxed.

Historical validation: a 128-training-row draft lacked training observations;
a 40-validation-row draft lacked loss-validation observations. A 512/1000,
batch-2, three-epoch Project8 run completed three iterations after native retries.
Some validation attempts stopped at 150 observations and about 415 ms. A later
four-epoch LIGO attempt still lacked epoch-0 training evidence at 128 batches
and about 491 ms. The final batch-1 default increases both observation counts
without changing runtime rules. These failures are retained as diagnostics.

## Inference timing evidence is not training admission

The pinned generic inference path records timing through
`InferenceRuntimeEvidence`. Its finalization does not call
`RuntimeVerificationSession.decide_admission`; an insufficient number of
inference batches can leave `steady_state_reached=false` while inference,
deliverable writing and scoring succeed. Training and epoch-loss validation
explicitly enforce admission and can reject an attempt. A completed demo is
therefore not evidence that every phase has a verified runtime prediction.
Preserve the native report; do not reinterpret a missing prediction as PASS.

## Executed final-default evidence (2026-09-30 UTC)

Source revision `222dc7b` was used for fresh projects outside both repositories,
with the pinned infra revision, its own frozen environments, RTX 5090, trusted
external credentials, 512/1000 events, batch size 1, four epochs and three search
iterations. The notebook invoked its generated Bash launcher; no direct
training entrypoint replaced that path.

| Task | Native exit | Seconds | Formal R2 in iterations 1, 2, 3 |
|---|---|---|---|
| Project8 dual | 0 | 1892.21 | -0.01827238, -0.00406507, -0.01030146 |
| LIGO | 0 | 1750.42 | -0.00480936, -0.00000371, -0.00094686 |

Both produced executed notebooks, HTML and score-versus-iteration PNG/SVG/CSV.
Native timing rejections were retained: one unscored `skipped_time_risk` record appears in
the Project8 plot CSV and five in LIGO. Missing scores are not fabricated;
negative scores use the unchanged plot boundary markers and retain raw CSV
values. These are successful workflow demos, not useful learned models or
scientific qualification. Neither task claims Health PASS.

Artifacts are local validation evidence under
`/tmp/project8-run-all-batch1-20260930` and
`/tmp/ligo-run-all-batch1-20260930`; these paths are not user prerequisites.
Both offline notebooks also ran in fresh paths with spaces, with all optional
save exercises enabled, no provider keys and no GPU launch. Focused tutorial
tests: 46 passed. Download parity covered both tasks' first selected rows,
plus a LIGO 64/60 cross-shard check across four raw files (36,766,272 bytes
transferred, exact local/remote array equality, no full-shard download).

Both full notebooks were replayed after removing enabled provider keys; they
reused recorded runs and the token-ledger SHA-256 stayed unchanged. Project8's
six saved Trial/Formal checkpoints were loaded through the native standardized
target loader on CPU. On four validation examples, zeroing either the time
channels or FFT channels changed the outputs, and all baseline outputs were
finite. Generated-source inspection also confirmed both views feed prediction.
This is bounded functional evidence, not a scientific attribution experiment.
