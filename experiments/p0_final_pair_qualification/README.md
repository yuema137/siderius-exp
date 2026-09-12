# Shared final-pair wrapper boundary

`common.sh` owns only checkout identity, required-input checks, fresh-workspace
refusal, inherited-environment clearing, and delegation. Task treatment values
remain in each task wrapper so their effective argv is visible and reviewable.

| task | Trial/Formal | train/eval cap | batch | VRAM GiB | probe s | worker GiB |
|---|---:|---:|---:|---:|---:|---:|
| TIDMAD | .01/.01 | 1024/omitted | 16 | 8/12 | 60/240 | 24 |
| Pets | 1/1 | 370/74 | 16 | 8/12 | 60/180 | 24 |
| DAVIS | .05/.05; eval .20 | 3/3 | 1 | 10/16 | 60/240 | 32 |
| Cancer MTG | 1/1 | full graph | 1 | 10/16 | 180/600 | 32 |

Every wrapper requests two iterations with two rounds each, one epoch, measured
Trial/Formal admission, and keeps runtime outputs outside this repository.
Actual stages require fresh runtime evidence; configuration alone is not a
qualification result.

## C2 runtime evidence index

The six task-package contract families are covered by the two synthetic CPU
format witnesses (SuperNEMO and MAJORANA) and four real workflows (TIDMAD,
Pets, DAVIS, and Cancer MTG). The real workflows exercise package binding,
scopes, Trial/Formal stages, metrics, Health semantics, continuation,
incumbent provenance, and external artifact ownership. Raw logs and workspaces
remain external.

| task (elapsed; bound) | actual scope and stages | metric / Health | continuity and incumbent | external evidence |
|---|---|---|---|---|
| TIDMAD (~12 min; 45 min bound) | file index 4, PSD units 15/174; Trial/Formal × 2; 1,024 train and 1,250/5,000 eval segments across iterations | Trial2 `-6.0728245` invalid; Formal scores null; Health collapse | 2 iterations; typed negative feedback restored; no incumbent; both Formal rounds invalid; launcher rc `1` captured | `/home/klz/Data/SIDERIUS/step04_tidmad_retry_HYKdjh.raw.log` and workspace |
| Pets (~8m33s; 30 min bound) | 370 train / 74 eval; Trial/Formal × 2; 37 classes and disjoint image IDs | all four accuracy `0.02702702702702703`; Health rejected collapse | 2 iterations; feedback restored; no eligible incumbent; both Formal rounds invalid; original rc not captured | `/home/klz/Data/SIDERIUS/step04_pets_restored_jgy4BZ.raw.log` and workspace |
| DAVIS (~18m29s; 30 min bound) | 3 train / 3 eval sequences; Trial/Formal × 2; sequence-disjoint scopes | Formal1 MSE `0.03889419312898538` → Formal2 `0.031130119241262407` (lower); Health passed | 2 complete iterations; incumbent restored and improved; original rc not captured | `/home/klz/Data/SIDERIUS/step04_davis_restored_zfYsP1.raw.log` and workspace |
| Cancer MTG (~15 min; 75 min bound) | full MTG graph; 3,717 train / 414 val masks; Trial/Formal × 2 | Formal1 AUPRC `0.26879417873942524` → Formal2 `0.18760729305813223` (higher direction); Health `EXPLICIT_NONE` | 2 complete iterations; prior Formal incumbent restored; best retained; original rc not captured | managed session `32429` stdout; `/home/klz/Data/SIDERIUS/step04_cancer_restored_5Lm7vl/workspace` (no raw log fabricated) |

CPU format witnesses (run earlier against infra `894a1dd4`, with identical
executable source): SuperNEMO and MAJORANA each ran isolated real
train/inference/scoring on synthetic task-format data, with disjoint
train/evaluation IDs, both classes, persisted histories/checkpoints, and
independent `energy_matched_roc_auc` checks. They make no original-data or
scientific claim.

All four pairs used infra `0dcec9c8e58a41f5aac4c62753dec54138d4d190` and exp
`f0be873a626becd54c3b949c2a4a2d4f5b28609f`; the CPU witnesses ran earlier
against identical executable source under that prior infra pin. Current
reproduction uses infra `3eb6d3d8529d4404b57d74422d3f0589669434b3`, recorded in
`SIDERIUS_REVISION` and the lockfile. Scientific Health rejection and
framework execution are reported separately; `no_records` is not silently
converted into a qualification score.

## Sanitized reproduction

From this exact checkout, follow the complete root credential procedure and
use the checkout's frozen `.venv`. Select one wrapper at a time, with its
required outer bound, fresh external workspace, and external raw log. Replace
only placeholders; do not put secrets, raw outputs, or runtime paths in Git:

| wrapper | required outer bound |
|---|---:|
| `oxford_iiit_pet` | 30 min |
| `davis_future_prediction` | 30 min |
| `cancer_gene_identification` | 75 min |
| `tidmad` | 45 min |

```bash
set -euo pipefail
# Follow README.md#api-backed-launch-preparation before this command.
unset PYTHONPATH
exec timeout --signal=TERM --kill-after=60s 1800s \
  bash experiments/oxford_iiit_pet/p0_final_pair_qualification/launch.sh \
  --siderius-checkout /path/to/SIDERIUS \
  --workspace /path/to/fresh/external/workspace \
  --data_dir /path/to/verified/data \
  > /path/to/fresh/external/run.raw.log 2>&1
```

Substitute the selected wrapper and its bound from the table; wrapper-specific
data roots and budgets are authoritative in each script. The managed
foreground session preserves the launcher's true exit status;
select the timeout from the table for each wrapper.

Evidence reviewed on 2026-09-12 covers 32 checks across the six task-package
contract families, the
earlier CPU pair, and these four real workflows. The old-pin runtime receipts
remain valid source-execution evidence because the infra update was
docs-only; they are not rerun results for the new pin. Known limits remain:
Pets, DAVIS, and Cancer original launcher exit codes were not captured, while
TIDMAD's retry exit code was captured as `1`; scientific Health rejection is
reported separately from framework execution.

## CPU task-format witnesses

The bounded SuperNEMO and MAJORANA witnesses exercise real CPU training,
inference, and scoring with synthetic task-format fixtures (no agent/API,
GPU, original data, or scientific claim):

```bash
cd /path/to/exact/siderius-exp-current
uv sync --group dev --frozen
.venv/bin/python -m pytest -q \
  --basetemp=/path/to/fresh/external/step04-basetemp \
  tests/test_step04_cpu_lifecycle.py -s
```

Use the exact pinned exp checkout and choose a new external basetemp for each
run. Pytest may clear that directory; never point it at original data,
existing results, or a shared repository location.
