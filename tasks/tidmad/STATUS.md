# STATUS — TIDMAD experiment package

This file records the external package's current qualification state. Framework
capability remains owned by the pinned SIDERIUS revision.

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
| data root | REFERENCE to the `tidmad_data_config.yaml` mechanism | `data/README.md` |
| run entrypoint | `quickstart.sh` — a thin adapter that requires an explicit SIDERIUS checkout, supplies this package's `composition.yaml`, and delegates to that checkout's `sdsc_submission_scripts/run_chain.sh`; it contains no framework code | separated dry-run against SIDERIUS `384cc9e8` |

**Nothing under `examples/tidmad/` is an authoring surface: the runtime does
not read these snapshots as a task authority.** They are generated
projections, and editing one changes nothing you want changed (design §3.6).
The one nuance: this package's composition manifest
`composition.yaml` binds `resolved/dataset_profile.json`
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

- `composition.yaml` resolves from `siderius-exp` against SIDERIUS `384cc9e8`
  with task-data-path id `tidmad`, primary metric
  `tidmad_denoising_score`, and semantic fingerprint
  `1d7aecac3a8af8dc53935be8ff6f0ba49d122a31b2991613e4f4c36c5fd9a364`.
- `quickstart.sh --dry-run` imports framework source exclusively from the
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
- The next separation step is removal of built-in real-task bootstrap imports
  from SIDERIUS while preserving the identity refusal and legacy TIDMAD parity.

## Maturity pins carried by this pack at PR0 (design §3.5)

- no production `.py` under `examples/` — valid through PR0 / Step 07;
  relaxation owner **D14**;
- no top-level `task_description` / `forward_contract` YAML under `examples/`
  — valid before Step 12; relaxation owner **Step 12**;
- `resolved/` snapshots must never coexist with a later real task binding as
  a second authoritative-looking config — migration owner Step 12 / D14.
