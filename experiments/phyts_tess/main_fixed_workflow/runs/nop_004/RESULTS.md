# `nop_004` — PhyTS TESS, no-prior arm, fixed workflow

The first TESS run to produce experiment records. Six hours, sixteen complete
iterations, one clean deadline stop.

Every number here is read from [`results.json`](results.json), which was
extracted from the unit's own persisted records rather than transcribed.

## What produced it

| | |
|---|---|
| unit | `nop_004`, started `2026-09-21T04:17:15Z`, deadline `2026-09-21T10:17:15Z` |
| arm | `no-prior` — treatment `phyts-tess-main-fixed-no-prior-v1` |
| treatment manifest sha256 | `3025de12dd4328a988e9d38db0c9c782ed87e4ef73f4bffaf5eb7b26d77f54fe` |
| siderius-exp | `12bd80af795be8402bab0dacfca6968054554b1d` (tag `v0.2.0-rc.22`) |
| SIDERIUS | `7689fd58b91d410788e953b51ea69a9dbc528a7d` (tag **`v0.2.8`**) |
| hardware | one `NVIDIA GeForce RTX 5090`, 32,607 MiB |
| provider key | `OPENAI_API_KEY` only — literature review and data analysis are both disabled in this arm |

**The pin matters.** exp master has since moved past `v0.2.8`. Reproducing this
unit means checking out exp at `12bd80a` and SIDERIUS at `7689fd58`, not
whatever the tree currently pins. `results.json` carries both, and the exact
argv the supervisor executed.

## Reproducing it

```bash
# 1. stage the data (two files by name; the tool refuses a destination
#    holding anything matching "test")
python tasks/phyts_tess/tools/stage_data.py \
    --source /path/to/TESS/parquet --dest /path/to/rundata

# 2. a SIDERIUS checkout at the pinned revision, with its own frozen venv
git -C /path/to/SIDERIUS checkout 7689fd58 && uv sync --group dev --frozen

# 3. preview first — this starts no clock and spends no budget
bash experiments/phyts_tess/main_fixed_workflow/launch.sh \
    --siderius-checkout /path/to/SIDERIUS \
    --data_dir /path/to/rundata \
    --unit_dir /path/outside/both/checkouts/nop_004_repro \
    --run_name tess_nop_004_repro \
    --arm no-prior
```

Add `--launch` to start. A fresh unit directory is required: `.chain_halted`
is never erased to retry, and the six-hour clock is written once.

Exact reproduction of the *scores* is not expected — the agents are LLMs and
the proposals differ run to run. What reproduces is the treatment, the
budgets, the scope and the evaluation.

## Results

Sixteen complete iterations, one trial round and one formal round each.
Iteration 17 was cut mid-formal by the deadline.

**The formal round is the measurement.** It trains on the whole pool and
evaluates on the complete 442-curve validation split, both operator-owned.
The trial round is the agent's own exploration and is reported for context.

| # | model | trial R² | **formal R²** |
|---|---|---|---|
| 1 | `cadence_aligned_spectral_resnet` | 0.7595 | 0.7131 |
| 2 | `cadence_spacing_pyramid` | 0.6679 | 0.7570 |
| 3 | `cadence_peak_relation_transformer` | 0.7479 | 0.7517 |
| 4 | `cadence_multitaper_expert_resnet` | 0.5832 | 0.6376 |
| 5 | `cadence_metric_aligned_expert_resnet` | 0.7372 | 0.8078 |
| 6 | `cadence_metric_bagged_ensemble` | 0.7586 | 0.7840 |
| 7 | `cadence_metric_query_pool_resnet` | 0.8015 | 0.7693 |
| 8 | `cadence_disagreement_calibrated_expert_resnet` | 0.7346 | 0.6133 |
| 9 | `cadence_highres_metric_expert_resnet` | 0.7769 | 0.7792 |
| **10** | **`cadence_independent_checkpoint_ensemble`** | 0.7874 | **0.8478** |
| 11 | `cadence_five_seed_checkpoint_average` | *0.2734* | 0.6691 |
| 12 | `cadence_crossfit_ridge_stack` | 0.8654 | 0.7941 |
| 13 | `cadence_genuine_oof_ridge_stack` | 0.5491 | 0.7910 |
| 14 | `cadence_temporal_checkpoint_soup` | 0.7535 | 0.7717 |
| 15 | `cadence_greedy_diverse_checkpoint_ensemble` | −1.8012 | **−1.7915** |
| 16 | `cadence_quadratic_best_r2_ensemble` | 0.6923 | 0.7692 |

**Best: R² 0.8478**, iteration 10, `cadence_independent_checkpoint_ensemble`.
Secondary metrics for every round are in `results.json`; the best iteration's
RMSE is in cycles per day, the unit R² does not carry.

Iteration 11's trial is italicised because it trained on half the pool while
its formal round trained on all of it — see *Comparability* below.

### Trend

| | median formal | best formal |
|---|---|---|
| iterations 1–8 | 0.7543 | 0.8078 |
| iterations 9–16 | 0.7792 | 0.8478 |

The median moves +0.025 and the best +0.040. **This is suggestive, not
established** — see *What this run cannot answer*.

### Prediction record

The framework's own evaluation, `metric_order_signsafe_v2`, over a pool of 15:

```
confirmed 3   partial 5   refuted 7
```

The agent predicts a numeric target and its own refutation threshold before
each run. It is **systematically optimistic** — more predictions were refuted
than confirmed — but the thresholds bind: seven were actually struck.

## Comparability

**A trial score and a formal score are only comparable when both trained on
the same pool.** The agent controls the trial portion, and in iteration 11 it
chose `trial_portion=0.5` while the formal round used the whole pool. The
resulting 0.396 difference is a data-volume effect, not measurement spread.
Any analysis comparing the two rounds must read `trial_portion` from
`results.json` first. Fifteen of the sixteen iterations were same-pool.

**`batch_size=1` is a confound.** It appears in iterations 11 and 13, and in
both the trial score collapsed while the formal round recovered. Do not
attribute a trial-round drop to an architectural change without checking it.

## What this run cannot answer

**There is no replicate.** Each iteration produced exactly one formal record,
so formal-to-formal reproducibility was never measured. The gap between
0.8478 and 0.8078 therefore cannot be called significant. A future run that
wants to rank architectures needs the same architecture evaluated twice under
different seeds; this treatment does not do that.

**The published PhyTS figures are not comparable.** S4D 0.665, CNN 0.617 and
LinOSS 0.612 come from the appendix D.2 70/15/15 re-split, while this run uses
the released 80/10/10 split grouped by Gaia DR3 identifier. R²'s denominator
is the evaluation population's own variance, so the two are different
quantities.

**The held-out test split was never read.** No number here touches it.

## Health checks

The `phyts_tess_prediction_dispersion` gate fired on every scored round and
passed every time, including on iteration 15, whose R² is −1.79.

| model quality | R² | observed dispersion | floor `0.05` |
|---|---|---|---|
| healthy (18 rounds) | 0.58 – 0.85 | 0.353 – 0.576 | 7–11× |
| poor (iteration 11 trial) | 0.27 | 0.326 | 6.5× |
| **catastrophic (iteration 15)** | **−1.79** | **0.129** | **2.6×** |

**The floor as configured detects only literal collapse, and no failure in
this run was a literal collapse.** Promoting it to `blocking` at `0.05` would
add no protection. The data suggests a floor near `0.2` would have caught
iteration 15 while passing all nineteen healthy and poor rounds, but that
rests on a single catastrophic sample and is recorded as a candidate rather
than applied. See the threshold note in
[`tasks/phyts_tess/declared/task_health.yaml`](../../../../../tasks/phyts_tess/declared/task_health.yaml).

## Framework defects encountered

**29 of 62 training attempts (47%) were rejected by runtime verification**
before producing any record, across four distinct mechanisms. None is
fixable from the task side. Reported upstream as
[SIDERIUS#567](https://github.com/Galileo-Sandbox/SIDERIUS/issues/567), which
carries the replay oracle built from these attempts' own persisted timings.

The cost is bounded — a rejection spends about 4.5 s of compute plus one
planner call — but it consumes one of the round's three attempt slots, and
iteration 1 lost a whole round to it. `consecutive_fail_rounds` never exceeded
`1/3`, so the chain was never at risk of halting.

Two earlier defects were already fixed in the pinned revision and did not
recur: [#563](https://github.com/Galileo-Sandbox/SIDERIUS/issues/563) (the
iteration-2 lock violation) and
[#565](https://github.com/Galileo-Sandbox/SIDERIUS/issues/565).

## Outcome

Clean `deadline_stop` at the deadline epoch, process group killed as designed,
no `.chain_halted`, no crash. The unit is preserved and is not reused.
