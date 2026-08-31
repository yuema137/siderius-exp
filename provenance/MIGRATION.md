# Repository Separation Migration

## Source lineages

- Published SIDERIUS release: `v0.1.4`
- Published release commit: `98610b8ded2277598749cc05ab567e1b92902bde`
- Unpublished Gold repair source: `624e1a93942fbc745b4559848048c578d5dd3074`
- Migration decision date: 2026-08-29

## Rules

1. Copy before deleting source assets.
2. Record the source path and source commit for each migration batch.
3. Preserve bytes and hashes unless portability requires a reviewed change.
4. Keep portability changes separate from semantic changes.
5. Do not patch SIDERIUS from this repository.
6. File generic defects in SIDERIUS and pin the qualified repair revision.
7. Do not launch Gold Stage 2 without explicit operator authorization.

## Batches

| Batch | Source | Destination | Source revision | Status | Evidence |
|---|---|---|---|---|---|
| Bootstrap | repository boundary and dependency pin | repository root | `98610b8ded2277598749cc05ab567e1b92902bde` | complete | commit `108dea0` |
| Gold source import | Gold protocol, task overlay, launchers, and evidence | `campaigns/tidmad_gold` | `624e1a93942fbc745b4559848048c578d5dd3074` | imported, not yet portable | byte equality plus `tidmad_gold_import_sha256.txt` |
| Real task import | TIDMAD, Oxford-IIIT Pet, and DAVIS packages | `tasks/**` | `624e1a93942fbc745b4559848048c578d5dd3074` | imported, not yet portable | byte equality plus `real_task_import_sha256.txt` |
| Cancer Gene import | Cancer Gene Identification package | `tasks/cancer_gene_identification` | `41c030721` | imported, not yet portable | byte equality plus `real_task_import_sha256.txt` |
| Composition portability | four real task manifests | imported task packages | current migration head | composition-only validation passed | `validation/2026-08-29_external_composition.md` |
| Cancer real-data checkpoint | complete NatureBench task plus bounded workflow | external data root and `tasks/cancer_gene_identification/workflows/**` | NatureBench `9e6a69f10865dd56f4991b49d1c974e2006b6b18`; SIDERIUS `8be2874d536a30e20a202e7d36568b596439e392` | 5090 data identity and materialization passed; GPU chain pending | `validation/2026-08-29_cancer_real_data_acquisition.md` |
| Pets package-test ownership | Oxford-IIIT Pet composition, provenance pins, split isolation, and external quickstart boundary | `tests/tasks/oxford_iiit_pet/test_package_contract.py` | SIDERIUS `63b98b58bd18b91ee840b8d1326bb292ef8cd893` | external task-owned checks pass after SIDERIUS removes the duplicated real-task package and runtime implementation | focused local pytest against the exact checkout |
| TIDMAD Stage-3 and reference ownership | Stage-3 writers, campaign-owned scorer and anchor resolution, adversarial witnesses, task-owned reference loader, and 54 frozen reference artifacts | `campaigns/tidmad_gold/stage3`, `tasks/tidmad/runtime`, `tests/campaigns/tidmad_gold/stage3`, `tasks/tidmad/reference_data` | SIDERIUS separation worktree after `63b98b58bd18b91ee840b8d1326bb292ef8cd893` | external ownership complete; SIDERIUS no longer loads TIDMAD evidence for an undeclared reference source and removes 52 duplicated reference/result files; its legacy scoring CLI retains one anchor-map copy until both migrate together | exact frozen values pass through the external loader; the reference and complete Gold campaign suite passes against the edited framework checkout |
| Literature ownership checkpoint | TIDMAD literature settings remain in the task package while SIDERIUS requires explicit caller settings and writes the cache under the run workspace | `tasks/tidmad/framework_configs/lit_review.yaml` plus the exact dependency pin | SIDERIUS `97523a99df436179c673db0abcfaa0ce8d8042e4` | qualified | 53 external task/boundary tests and 116 Gold campaign tests pass against the exact checkout; Ruff passes |

## Framework blockers discovered during separation

| Issue | Boundary | Status |
|---|---|---|
| SIDERIUS #383 | composed Health binding through round evaluation | repaired and externally witnessed at `8be2874d` |
| SIDERIUS #384 | task-valid semantic targets in VRAM admission probes | repaired and externally witnessed at `8be2874d` |
| SIDERIUS #385 | task-valid context in generic deliverable writing | repaired and externally witnessed at `8be2874d` |
| SIDERIUS #386 | TIDMAD configuration resolution during generic workflow import | repaired and externally witnessed at `8be2874d` |
| SIDERIUS #387 | non-applicable proposal preflight converted null factor with `float(None)` | reproduced by Cancer qualification and repaired at `52e3e8e0` |

## Pending ownership reconciliation

| Boundary | Current evidence | Required next decision |
|---|---|---|
| Legacy reference retirement | the external task loader reproduces the exact floor, ceiling, and ruler values; SIDERIUS returns a named absence when no reference source is declared | complete; future generic reference evidence requires a typed caller-owned declaration rather than an implicit compatibility path |
| TIDMAD Gold launcher portability | the entrypoint now requires an exact SIDERIUS checkout, executes that checkout's existing chain, and binds campaign-owned task and Health files; Stage-1 external dry-run and Stage-2 refusal pass | reconcile the broader imported deployment preflight and complete release/H100 qualification without changing frozen treatment or adding a second execution mechanism |

## Portability changes

| Date | Paths | Change | Semantic effect |
|---|---|---|---|
| 2026-08-29 | four task `composition.yaml` files | replace former in-repository `examples/**` references with package-local references; load real task data paths through `file:` rather than built-in module imports | none; ownership and path resolution only |
| 2026-08-29 | `tasks/tidmad/framework_configs/**` | assign collision-free responsibility names to four source files formerly named `tidmad.yaml` in separate directories | none; file contents remain byte-identical |
| 2026-08-29 | `tasks/tidmad/declared/task_config.yaml` | import the task declaration previously resolved from the SIDERIUS repository default | none; makes task ownership explicit |
| 2026-08-29 | `tasks/cancer_gene_identification/workflows/**` | separate bounded two-network qualification from the complete eight-network formal campaign | qualification scope is intentionally smaller; formal task scope is unchanged |
| 2026-08-29 | `tasks/cancer_gene_identification/quickstart.sh` | require an explicit SIDERIUS checkout and select an explicit workflow | removes repository-co-location dependence; scientific behavior remains owned by the selected workflow |
| 2026-08-30 | Oxford-IIIT Pet qualification launcher | move the two-iteration treatment from `tasks/oxford_iiit_pet/quickstart.sh` to `experiments/oxford_iiit_pet/two_iteration_qualification/launch.sh` | none; resolved launch values are preserved while static task ownership is separated from experiment policy |
| 2026-08-30 | Oxford-IIIT Pet bounded composition | name the reusable task-owned scope as `tasks/oxford_iiit_pet/compositions/bounded_qualification.yaml` and let the experiment select it explicitly | none; task semantics and scope identities are unchanged, while composition selection becomes experiment-owned |
| 2026-08-30 | DAVIS qualification boundary | move the two-iteration launcher to `experiments/davis_future_prediction/two_iteration_qualification/` and name its selected task-owned scope `tasks/davis_future_prediction/compositions/bounded_qualification.yaml` | none; the 60/15 clip scope, lower-is-better metric, objective, and exact launch treatment are preserved |
| 2026-08-30 | Cancer-gene experiment boundary | move the shared launcher under `experiments/cancer_gene_identification/`, rename the two task-owned scopes as `compositions/two_network.yaml` and `compositions/eight_network.yaml`, and expose them as two ordinary experiments over the same Trial/Formal workflow | none; graph sets, metrics, objective, batch lock, and launch treatment are preserved; neither experiment becomes a campaign |
| 2026-08-30 | Multi-task campaign scaffold | add a common campaign package contract, retain TIDMAD Gold as the existing stopped campaign, and create non-launchable campaign packages for Pets, DAVIS, and Cancer with deployment ownership recorded separately | none; no campaign parameters, workflow semantics, authorization, or workload state changed |
| 2026-08-30 | TIDMAD qualification boundary | move the bounded two-iteration launcher from the static task package to `experiments/tidmad/two_iteration_qualification/`, name its selected task-owned scope `compositions/bounded_qualification.yaml`, and retire the duplicate imported root composition | none; all resolved Trial/Formal treatment values and task declarations are preserved; Gold compatibility assets remain pending campaign reconciliation |
| 2026-08-30 | TIDMAD Gold workflow ownership | move the calibrated Stage-1 Health source and unauthorized Stage-2 boundary from the static task package into `campaigns/tidmad_gold/workflows/`; retain the older materialized Health file as historical evidence only | none; gate roles, actions, thresholds, and Stage-2 refusal remain unchanged |
| 2026-08-30 | TIDMAD Gold external launcher paths | require an explicit SIDERIUS checkout, execute its existing `run_chain.sh`, bind campaign-owned task and Health files by absolute path, and validate the exact task file passed to the child | none; the frozen chain values, band topology, run identity, and Stage-2 authorization barrier are unchanged |
| 2026-08-30 | TIDMAD Gold LLM routing ownership | copy the frozen routing values from SIDERIUS `llm_configs/openai_tiered_pro.json` (source SHA-256 `17446b7ec367db1112159821c4493d19b3f3cbf40c5c927b5632e25ad654fa87`) into `campaigns/tidmad_gold/config/llm_routing.json` and resolve it from the campaign package | none; the exact role, provider, and model mapping is preserved, and SIDERIUS remains the generic parser authority |
| 2026-08-30 | TIDMAD Gold VRAM provenance repair | preserve the imported v0.1.4 `40/40` campaign default and make the dry-run row and launch manifest record the same effective values passed to every child | none; corrects stale `NOT_SUPPLIED` / `PENDING_H100_QUALIFICATION` reporting without changing admission values or interpreting units |
