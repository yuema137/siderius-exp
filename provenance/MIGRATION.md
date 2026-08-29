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

## Framework blockers discovered during separation

| Issue | Boundary | Status |
|---|---|---|
| SIDERIUS #383 | composed Health binding through round evaluation | open |
| SIDERIUS #384 | task-valid semantic targets in VRAM admission probes | open |
| SIDERIUS #385 | task-valid context in generic deliverable writing | open |
