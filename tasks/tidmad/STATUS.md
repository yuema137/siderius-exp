# STATUS — TIDMAD experiment package

This file records the external package's current qualification state. Framework
capability remains owned by the pinned SIDERIUS revision.

The projection checks named below are pre-separation evidence from the SIDERIUS
checkout. Equivalent package-local ownership is still pending in M4; they must
not be presented as tests executed from this repository.

## Maturity: **production-backed task package; separated qualification pending**

| projected in this pack (PR0) | how | verified by |
|---|---|---|
| `DatasetProfile` | `resolved/dataset_profile.json` — GENERATED, DO NOT EDIT | `tests/unit/examples/test_tidmad_projection.py` (deep-compare vs `resolve_dataset_profile()`) |
| `ModelIOContract` | `resolved/model_io_contract.json` — GENERATED | deep-compare vs `run_bound_model_io_contract()`; class axis fixed 256 pinned |
| `DeliverableSpec` | `resolved/deliverable_spec.json` — GENERATED | deep-compare vs `derive_tidmad_deliverable_spec()` |
| `MetricSpec` (golden metric) | `resolved/metric_spec.json` — GENERATED | deep-compare vs `derive_tidmad_metric_spec()`; `id == tidmad_denoising_score`, `direction == higher` pinned as literals |
| identity (file indices + file families) | `resolved/identity.json` — GENERATED | deep-compare |
| task description / forward contract | REFERENCE to `configs/task_config.yaml` | README cites the owning path |
| health policy | REFERENCE to `configs/health_checks.yaml` | README cites the owning path |
| data root | explicit caller-owned `--data_dir` argument | `data/README.md` |
| run entrypoint | experiment-owned `experiments/tidmad/two_iteration_qualification/launch.sh`, which selects `compositions/bounded_qualification.yaml` and delegates to the pinned checkout's `sdsc_submission_scripts/run_chain.sh` | two-iteration separated dry-run against SIDERIUS `7476bf44` |

**Nothing under `examples/tidmad/` is an authoring surface: the runtime does
not read these snapshots as a task authority.** They are generated
projections, and editing one changes nothing you want changed (design §3.6).
The one nuance: this package's composition manifest
`compositions/bounded_qualification.yaml` binds `resolved/dataset_profile.json`
and `resolved/metric_spec.json` as declaration references, so a composed run
does load those two — which is exactly why a hand edit is caught as a red
test rather than being harmless.

## NOT projected here (and who owns it)

| seam | status | owner |
|---|---|---|
| task-owned data preparation | not projected — TIDMAD's acquisition is owned by the paper's own repository, and this pack ships no fetcher (`PROVENANCE.md`, `data/README.md`) | upstream (the TIDMAD distribution) |
| model / loss plugins, skills, `configs/` inside the pack | not projected (no consumer-less files, roadmap §22.23.3) | Step 12 (composition) |
| task binding of the pack as a whole | `configs/task_config.yaml` remains the single runtime task authority | Step 12 |
| training-history / diagnosis semantics | **production-backed from 07a** (Step 07 PR 07a): the production trainer emits R2 + R3 (`training_history`) and the tuner persists the derived `training_diagnosis` on every `ExperimentRecord` (`run_output_*.json`); NO new `resolved/` snapshot — the history is per-run evidence, not task config; hidden from both LLM-facing renders until 07b | landed (07a); rendering 07b; interpretation Step 09 |
| metric-direction policy / planner-reflector rendering | **production-backed from 07b** (Step 07 PR 07b): the tuner's every golden-metric ordering decision — trial winner, skip/bypass orientation and their disabled sentinels, the bootstrap sentinel, the planner's score-table incumbent, the reflector's best/rank/new-best/efficiency band, and all five `best_*` finalization tracks — flows from ONE `MetricOrder` derived from this pack's `direction: higher`; the planner and reflector prompts render this pack's task content, direction wording, metric identity and compact `TrainingDiagnosis` lines from their landed authorities | landed (07b); peripheral direction consumers (chain / resume / `per_file_best` / dashboard) remain **Steps 09/10/M2** |
| measurement / verification data feeding | not yet landed | Step 07c |
| generic health applicability declaration | `configs/health_checks.yaml` referenced only | Step 08 |
| interpretation evidence | — | Step 09 |

## Separation qualification

- `compositions/bounded_qualification.yaml` resolves from `siderius-exp`
  against SIDERIUS `7476bf44` with task-data-path id `tidmad`, primary metric
  `tidmad_denoising_score`, and semantic fingerprint
  `1bfbd291921ce56063420fa8d9c973c9f3d7abf4e8b1a5b76cd604c0a07d4252`
- the qualification dry-run resolves two iterations and two tuner rounds, with
  Formal scope and evaluation fixed at `0.02`
- Gold Stage 1 Health treatment is stored separately with
  `amplitude_collapse` as its sole blocking gate; Gold Stage 2 remains
  non-executable and unauthorized
- the qualification launcher's `--dry-run` imports framework source exclusively from the
  explicit SIDERIUS checkout, uses this package's composition, and emits
  `--min_formal_batch_size 1` so the qualification does not reintroduce the
  invalidated Formal-only batch guard.
- Literature review resolves from the task-owned
  `framework_configs/lit_review.yaml`; a composed run does not consume the
  framework checkout's task-specific default.
- A fresh small-scale real-data RTX 5090 run completed task-owned literature
  review (2 findings, 3 search rounds, 19 papers), cold-start proposal,
  implementation, all seven model-validation checks, and resource admission.
  Training then refused before model execution because the child had already
  registered SIDERIUS's built-in `tidmad` implementation while the parent had
  pinned this package's byte-identical implementation. Their source SHA-256
  values are both
  `bd92af5ac9cfc19e4e8df2921db18ced40b9384c6d46b75884cbf454618e21b9`,
  but their module identities differ. The run was stopped before redundant
  retries and remains unscored diagnostic evidence.
- SIDERIUS `5ccecd4f` removes import-time real-task registration and retains an
  explicit legacy TIDMAD bootstrap. A fresh child-process witness resolved this
  package's transported `TidmadTaskDataPath` with the parent-pinned identity.
- Qualification workspace `ee67858_5ccecd4f_5090_chain` completed 2,500
  training steps in 158 seconds and wrote a valid checkpoint. The original
  generic inference path then retained raw `[256, 16000]` predictions for the
  complete 5,000-sample evaluation scope and was killed before persistence.
  SIDERIUS issue #391 records the generic eager-materialization defect.
- Against SIDERIUS `a4e63655`, an inference-only delta witness streamed the
  same checkpoint and scope at batch 32: 5,000 samples, 157 batches, four
  task-owned HDF5 deliverables, and 74.99 seconds. The frozen
  anchor-normalized metric then returned a finite score of
  `-10.509863893769241`. This proves execution closure for the repair; it is
  not a scientific-performance result and does not make the stopped chain an
  authoritative completed iteration.
- SIDERIUS `d53ac914` repairs the independent time-warmup scope-identity
  coupling by passing the attempt's existing task-owned scope to the bound
  external data path. A real RTX 5090 witness measured two batches at a median
  `48.1323 ms`. A fresh uninterrupted end-to-end qualification remains pending.
- Qualification workspace `7299c3e_d53ac914_5090_chain` exercised that repair
  through the production chain. The measured warmup admitted the run at
  `47.12 ms` per step; training completed 2,500 steps in 163 seconds, generic
  inference streamed 5,000 samples in 157 batches and 54.93 seconds, four
  deliverables were scored, and Health correctly invalidated a constant-output
  model. Attempt persistence then failed because generic inference had written
  a summary dictionary to the legacy per-file timing sidecar. SIDERIUS issue
  #393 tracks the generic schema mismatch; `7476bf44` provides its focused
  repair. The operator stopped the unchanged automatic retry, so this run is
  diagnostic evidence rather than a completed iteration.
- Fresh workspace `358ba13_7476bf44_5090_chain` accepted the #393 repair:
  training, streamed inference, scoring, Health, and attempt persistence all
  completed; the timing sidecar was the declared empty list and the attempt
  persisted as `failed_mode_collapse`. Formal admission then priced the
  launcher's inherited complete evaluation scope at more than 30 minutes. The
  repeated attempts were stopped because reducing model capacity could not
  change that scope. The package quickstart now pins
  `--formal_eval_portion 0.02` alongside its other bounded portions; its
  production dry-run resolves that exact value. A fresh complete iteration
  remains pending.

## Maturity pins carried by this pack at PR0 (design §3.5)

- no production `.py` under `examples/` — valid through PR0 / Step 07;
  relaxation owner **D14**;
- no top-level `task_description` / `forward_contract` YAML under `examples/`
  — valid before Step 12; relaxation owner **Step 12**;
- `resolved/` snapshots must never coexist with a later real task binding as
  a second authoritative-looking config — migration owner Step 12 / D14.
