# External Task Composition Validation — 2026-08-29

## Purpose

Prove that each imported real task manifest composes from `siderius-exp` through the public SIDERIUS task-composition boundary, using a clean checkout of the exact pinned framework revision rather than importing the developer's active checkout.

## Framework

- SIDERIUS commit: `98610b8ded2277598749cc05ab567e1b92902bde`
- SIDERIUS source checkout: detached worktree at the pinned commit
- Python environment: the SIDERIUS project virtual environment
- Operation: `compose_run_task_bindings` only
- No training, inference, scoring, network access, or dataset access

## Results

| Manifest | Resolved task-data-path id | Result |
|---|---|---|
| `tasks/tidmad/composition.yaml` | `tidmad` | PASS |
| `tasks/oxford_iiit_pet/compositions/bounded_qualification.yaml` | `oxford_iiit_pet` | PASS |
| `tasks/davis_future_prediction/composition.yaml` | `davis_future_prediction` | PASS |
| `tasks/cancer_gene_identification/composition.yaml` | `naturebench_cancer_gene` | PASS |

## Findings

The first run failed only because the imported manifests still referenced their former `examples/**` locations. Replacing those references with package-local paths and selecting the copied data-path implementations through the existing `file:` contract made all four manifests compose successfully. No framework source change or new loading mechanism was required.

Every invocation also emitted a TIDMAD configuration warning while importing the generic workflow, including non-TIDMAD tasks. This is recorded as SIDERIUS issue #386. The warning did not change the composition verdict and was not suppressed.

## Remaining boundary

Composition success establishes declaration and plugin resolution only. It does not establish child-process execution, resource admission, inference, deliverable writing, or scoring. Those remain separate validation stages, including the open SIDERIUS issues recorded in `provenance/MIGRATION.md`.
