# One-band TIDMAD tutorial contract

## Ownership and public files

`project` copies the task and notebook into a fresh external project, writes
an initial `TidmadExperiment` JSON and a shell entrypoint bound to the exact exp
interpreter. `write_file_split_task` writes a new composition containing a
validated `FileSplit` constructor value. That inline declaration participates
in composition fingerprinting. Notebook save cells create the task YAML,
experiment JSON and matching shell scripts; read-back cells inspect disk rather
than relying on in-memory settings. Notebook cells never launch or call APIs.

`runner` reuses shared location/GPU/environment/source checks and workflow
rendering with explicit TIDMAD workflow/treatment paths. TIDMAD NoPrior retains
literature review, binding the external task's `framework_configs/lit_review.yaml`
through `--ml_lit_review_config`; data analysis and advice are disabled. Source checkouts must
be clean and pins exact. Missing exported credentials refuse before data/GPU
checks. Preview reports key names/booleans only. Result authority is diagnostic;
blocking Health is preserved. No total campaign clock/spending cap is supplied.

## Two data entrances

`data_entry.use_existing_tidmad` verifies the eight band source hashes, then
creates eight symlinks into the user's run-data view. It never copies or mutates
raw HDF5. Conflicting existing entries refuse; repeating the same binding is
allowed. The view contains only those links and the committed small anchor.
The source may expose other bands; the view does not. This is not an OS access
barrier. Source availability and unchanged bytes remain launch prerequisites.

The independent download entrance is the official downloader with four train,
four validation and zero science files, targeting the same run-data view. Both
entrances undergo `verify_band_inputs` before launch. For TESS, the shared
helper verifies existing pinned Parquet bytes and reuses the task staging
converter to write only its required train/val NPZ format; it does not download
or copy raw Parquet and refuses an existing destination.

## Paper pool versus file holdout

`paper-pool` selects `TidmadFrozenPoolDataPath` and locks
`formal_train_fraction=0.1`: the complete 20/200 parent pool. Trial fractions
sample within those 20. Evaluation retains original per-file 200-segment scopes.

`file-holdout` selects task-owned `FileSplitDataPath`, which inherits the ordinary
TIDMAD data path, not the frozen-pool capability. `FileSplit` requires nonempty,
duplicate-free, pairwise-disjoint train/validation/test file groups whose union
is exactly 0..3. Defaults are train=(0,1), validation=(2,), test=(3,). Training
materialization reads the training family; validation and final testing read
the validation family. Every original segment 0..199 remains eligible within an
assigned file; there is no FFT catalog, tone-confidence filter or frequency-label
inference. This is file/range separation, not exact frequency non-overlap.

Ordinary scope fractions select ceil(portion*200), at least one, with per-file
seeded sampling. Per-epoch `formal_train_portion` stays 1.0. Workflow scope methods
can return only train/validation groups; `build_final_test_scope` is called only
by the separate final entrypoint. The adapter accepts snapshot strategy,
subset_ref whose parsed file set is 0..3 (both range and canonical CSV spelling), no target partitions, and model window 40000. CLI Health coverage
is explicitly the selected validation file group, not the union of all four
indices; raw band staging and data_scope remain 0-3. Model I/O, serialization,
materializers, scoreability, metric arithmetic and Health thresholds are reused.

## Final-test lifecycle

The launcher explicitly retains original training checkpoints for final testing.
`candidate_for_record` resolves a user-selected successful native attempt from a
run record inside the experiment workspace and requires both run and attempt
task fingerprints to match the selected composition. It never selects a winner.
`Candidate` names that run record and the selected native model, model/loss configs, checkpoint,
success sentinel and generated-library tree. The operator attests search has
stopped. `--seal` creates a fresh output and records candidate artifacts, task
composition fingerprint, experiment digest and source revisions before test
inference. `--evaluate` refuses changed selection and verifies source data/GPU.
An exclusive start marker prevents unnoticed retries, including after failure.

The pinned native inference child receives the explicit final sample_set,
profile/model-I/O contracts, task manifest and selected generated library.
Provider key variables ending `_API_KEY` are removed from its environment.
After inference, the selected composition's data path reads deliverables and
constructs the final scope; its metric handle enforces its scoreability contract
before arithmetic. Nonfinite metric values serialize as null with finite=false.
The standalone result explicitly records Health as not assessed and authority
as diagnostic; it is not a full workflow evaluation or paper qualification.

No OS-private holdout, concurrent-process shutdown or global one-shot ledger is
promised. Users who use final scores for model selection consume the holdout.

## Validation evidence

The real shared TIDMAD 0-3 inputs at the operator-provided path matched all eight
frozen SHA256 values, and existing TESS Parquet matched the pinned source
manifest. No raw data was downloaded. Original segment IDs and bytes remain
unchanged. Earlier single-segment native CPU inference preserved 10M input and
target samples exactly and exercised composed scoring; its synthetic metric
was nonfinite, not a scientific success. Current tests cover file partition
refusals, scope construction, fraction counts, fingerprint changes, validation
Health coverage flags, source-link reuse, selection sealing and missing-key
refusal. Notebook and API/GPU qualification evidence must be reported separately.

Current file-split validation (2026-09-29): 80 focused tests passed. Both notebooks
completed default and opt-in save/read-back execution against the existing
shared data, with no download. TIDMAD staging used symlinks; TESS performed only
the required NPZ conversion. The TESS re-split example also regenerated its
matching task/data pair. Executed notebook outputs remain external; committed
notebooks contain no outputs or execution counts.

Real API/GPU smoke on 2026-09-29 used exp `62c7e66`, the pinned infra, RTX 5090,
existing shared HDF5, and externally injected credentials. One iteration / one
epoch, Trial train/eval .01/.01, Formal .02/.02, 2/5 minute training allowances
and 8 GiB completed two Trial attempts and one Formal attempt in about 9 minutes
(13 LLM calls, 150289 reported tokens). Persisted training scopes contained only
files 0,1; evaluation and training-validation scopes contained only file 2.
Training, inference, checkpoint retention and record persistence executed.
All three attempts were `failed_mode_collapse`, with null scores; the chain
exited 1 with `no_records`. The final-candidate helper correctly refused the
real failed attempt. No final-test inference was run, and file 3 was not used
for model selection. This is an execution/failure-handling witness, not a
successful denoising result or completed final-test qualification. Do not treat
the tiny smoke settings as a recipe for a useful model. Local evidence lives
under `/tmp/tidmad-file-smoke-003-20260929`; it is not a portable input dependency.
