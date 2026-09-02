# siderius-exp

Private scientific task packages, campaigns, deployment configuration, and experiment provenance for SIDERIUS.

This repository is a consumer of the [SIDERIUS](https://github.com/Galileo-Sandbox/SIDERIUS) framework. It contains no framework fork. Every qualified experiment pins an exact SIDERIUS commit and uses only supported task-composition and plugin contracts.

## Repository boundary

- `tasks/` owns real scientific task packages and task-specific plugins.
- `campaigns/` owns frozen treatments, launch policy, budgets, and campaign records.
- `deployments/` owns explicitly configured infrastructure and scheduler surfaces.
- `experiments/` owns run manifests, result indexes, and reproducibility receipts.
- `provenance/` owns migration and source-lineage records.

Lightweight synthetic examples remain in SIDERIUS so the framework can validate its complete supported lifecycle without this repository.

## Independent ownership axes

| Axis | Owns |
|---|---|
| task | scientific semantics, data identity, objective, metrics, validity definitions, and task plugins |
| workflow | execution procedure, including Trial/Formal roles, round progression, promotion, retry, and persistence mechanics |
| experiment | one concrete task + workflow selection and its treatment values, advice, budgets, and result identity |
| campaign | coordination of multiple runs, arms, bands, or stages, including authorization and cross-run selection |

Trial and Formal belong to a workflow. Their presence does not make a run a
campaign: an ordinary experiment and a campaign stage may select the same
Trial/Formal workflow with different approved treatment values.

## Framework revision

The active dependency is pinned in `pyproject.toml` and repeated in `SIDERIUS_REVISION`. A scientific run must additionally record both repository commit SHAs in its run provenance.

## Repository identity and linked worktrees

A linked Git worktree may live outside the primary checkout, including under
`/tmp`. Its filesystem location does not determine repository ownership. Before
editing, committing, launching, or reporting task work, verify all four values:

```bash
git rev-parse --show-toplevel
git rev-parse --git-common-dir
git branch --show-current
git remote get-url origin
```

Task, experiment, campaign, deployment, and scientific-provenance changes must
resolve to this repository's common Git directory and remote. They must never be
added to the SIDERIUS framework checkout. A temporary-looking linked-worktree
path must be described as a linked worktree, not as an unowned temporary output.
Work is not durably part of `siderius-exp` until it is committed on an identified
branch and pushed to this repository's remote.

Raw data, generated workspaces, model artifacts, caches, and secrets are runtime
state rather than repository content. Their configured external paths may be
temporary or machine-persistent, but they must not be committed here.

## Active classification tasks

- `tasks/supernemo_signal_background/` owns event-level SuperNEMO
  signal/background classification with fixed 25-keV energy matching.
- `tasks/majorana_low_avse/` owns fixed-length Majorana Demonstrator waveform
  classification for `psd_label_low_avse`, also with fixed 25-keV energy
  matching. It uses the Zenodo partial release's official Train/Test boundary;
  unlabeled NPML files never enter supervised execution.

The corresponding `experiments/` launchers keep bounded qualification separate
from 20-iteration scientific campaigns. Literature ON and OFF runs must use
fresh workspaces and differ only in the declared literature switch.

## Migration status

The repository boundary is being established from the SIDERIUS `v0.1.4` release and the unpublished `v0.1.5` Gold repair lineage. See `provenance/MIGRATION.md`. No campaign is authorized to launch merely because its files exist here.
