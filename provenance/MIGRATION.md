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
| Pets package-test ownership | Oxford-IIIT Pet composition, provenance pins, split isolation, and external quickstart boundary | `tests/tasks/oxford_iiit_pet/test_package_contract.py` | SIDERIUS `2406dadd8dc3e80d87733cdc1a68494d3d8cead7` | external task-owned checks pass; SIDERIUS source deletion remains pending responsibility-level comparison with the historical test modules | focused local pytest against the exact checkout |

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
| TIDMAD Gold workflow assets | `tasks/tidmad/workflows/gold_stage1/health_checks.yaml` carries the calibrated amplitude-only blocking treatment, while `campaigns/tidmad_gold/task/health_checks_effective_gold.yaml` is an older materialized artifact with equivalent gate actions but stale rationale text; Stage 2 has no executable task launcher | establish the campaign-owned authoritative source before removing the task-side compatibility copies; do not merge or rewrite scientific treatment implicitly |

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
