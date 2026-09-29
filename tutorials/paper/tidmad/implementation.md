# One-band TIDMAD tutorial contract

## Ownership and protocol boundaries

`project` copies the complete task to an external project and installs shell
entrypoints bound to the exact exp checkout interpreter. `runner.TidmadExperiment`
extends the TESS teaching settings solely to reuse location, budget, source,
GPU and environment checks; it overrides the version and protocol semantics.
The shared renderer takes explicit workflow/treatment paths, retaining its
original TESS defaults. TIDMAD uses its main fixed workflow and NoPrior treatment:
literature review enabled, data analysis and advice disabled. Band and Health
coverage are `0-3`. Result authority is diagnostic; blocking Health remains on.

`paper-pool` selects `TidmadFrozenPoolDataPath`; `formal_train_fraction` is locked
to 0.1 because it declares the original 20/200 frozen parent. Trial training
fractions apply within those 20. Evaluation retains the original independent
200-segment population. `frequency-holdout` selects the new task-owned
`FrequencySplitDataPath`, which inherits the ordinary TIDMAD data path, not its
frozen-pool capability. Formal fractions then sample the frequency-eligible
training population; per-epoch `formal_train_portion` remains 1.0.

## Frequency identity and scope construction

`FrequencyCatalog` requires every (family, file, segment) in training/validation
× 0..3 × 0..199 exactly once and eight source SHA256 values. `FrequencySplit`
partitions all observed integer-Hz frequency identities into three nonempty,
disjoint sets. Every population must retain a segment in every band file to
preserve declared Health coverage. A seed shuffle partitions distinct frequency
identities; requested fractions use ceil, so realized sample fractions need not
match frequency fractions. The user must inspect counts and amplitude balance.

Only training-family rows in train_hz enter training. Only validation-family
rows in validation_hz enter workflow evaluation. Only validation-family rows in
test_hz enter standalone final inference. Other family/group combinations are
excluded, not moved, renamed, or Fourier-masked. Original segment indices are
preserved so raw data, deliverables and existing scoring anchors stay aligned.
The full validated split is a composition constructor value and participates
in semantic fingerprinting. Sampling is seeded per file, ceil(portion*N), at
least one. The adapter accepts only snapshot selection, subset_ref `0-3`, no
target partitions and segmentation_size 40000. Serialized scopes reuse the
base task contract; model I/O, materializers, scoring and Health are unchanged.

## Catalog inspection limits

`catalog` verifies frozen source hashes, reads all clean channel-2 segments,
then verifies source hashes again. For each complete 10M-sample segment it
identifies a dominant FFT bin, requiring at least 80% non-DC spectral energy,
and agreement within 10 Hz with ten subwindows. It maps that observation to the
nearest declared nominal tone within 10 Hz, retaining the observed peak in each
row. This prevents small peak-bin drift from splitting one nominal injected tone. This is an explicit conservative
inspection heuristic for injected sinusoids, not a general multi-tone detector
or an established source frequency authority. Ambiguity aborts with file/segment
identity. No partial catalog is written. Human review is required via
`catalog_reviewed` before launch; the flag is an operator attestation, not proof.

The historical frequency reference list is not treated as a per-file/per-segment
mapping. Exact nominal-frequency grouping does not impose a guard band or prevent
nearby-frequency/harmonic generalization. Real-band scanner qualification remains
outstanding; no test using synthetic tones establishes real-band adequacy.

## Final-test lifecycle and limitations

`final_test.Candidate` names one native generated model, its exact model/loss
configs, checkpoint, successful-training sentinel and generated-library tree.
The operator attests `search_completed`. `--seal` creates a fresh output directory
and records selection hashes before inference. `--evaluate` requires identical
selection, reviewed source-bound split, source pins, verified original data and
supported GPU. An exclusive `test-started.json` prevents unnoticed retries in the
same directory, including after failures. The subprocess invokes the pinned
native inference module in agent-model loading mode (this is not an LLM call),
with the held-out original sample_set and explicit task/profile. Provider key
variables ending in `_API_KEY` are removed from that child environment.

Scoring invokes the selected composition metric handle, including its declared
scoreability contract, with the task-owned final-test scope and evaluation
payload. The TIDMAD handle delegates arithmetic to its `score_vector`, using the
existing anchors and original segment identities. No new metric formula or
selection loop exists here. The standalone result is diagnostic and explicitly
records Health as not assessed. It is not a paper qualification or replacement
for framework evaluation policy. Files remain locally readable and no OS-level
holdout isolation, concurrent-process shutdown, or global one-shot ledger is
promised. A user who adapts models to final results has consumed the holdout.

## Validation boundaries

Tests cover catalog completeness and overlap refusals, frequency-relative
sampling, composed scope construction/serialization, fingerprint changes,
renderer fractions/treatment and external initialization. Notebook execution
uses an initialized external project and the exact exp kernel. Synthetic tests
cannot certify released-data frequency mapping, real-model output, calibration,
Health, or final-test scientific quality. No paid TIDMAD search has been run.

Observed offline validation (2026-09-29): 79 focused tutorial/workflow/TIDMAD
materialization tests passed. The notebook completed with an external project
and exact exp kernel. An additional CPU native-inference probe loaded a synthetic
identity-model checkpoint through the pinned infra child, selected original
segment 9, and preserved all 10M input/target samples byte-for-byte in the
persisted deliverable. The unchanged scorer executed on that synthetic artifact
and returned nonfinite (-inf), not a scientific success. The catalog heuristic
identified its known injected 2000 Hz tone. This fixture neither uses official
raw data nor qualifies real candidate performance or full-band cataloging.
