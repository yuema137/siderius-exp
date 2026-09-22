# Prepared LIGO and Project 8 workflow qualification

## Scope and review

This additive change introduces two external task compositions and NoPrior fixed
workflow experiments. Framework pin: `0ab1573602c708ddd182432ad4d0e43ae4828c53`
(`v0.2.11`). Existing TIDMAD tasks, experiments, dependency pins and framework
source are unchanged. Review covered task semantics, exact split coverage,
metric direction, training freedom, credential handling, process ownership,
immutable deadlines and clean-source launch preflight. This is operator review,
not a claim of an independent reviewer or unobserved CI results.

The prepared views preserve the released training/validation splits and the
owner-supplied paper preprocessing. They contain no test set, clean/noise
components or auxiliary source truth. Local deployment records retain array
hashes and source/preprocessing receipts; large arrays remain outside Git.

## Verification

Using this checkout's frozen environment:

```bash
.venv/bin/python -m pytest -q \
  tests/tasks/test_prepared_regression.py \
  tests/experiments/test_prepared_unit.py \
  tests/experiments/test_fixed_workflow_config.py \
  tests/experiments/test_workflow_credentials.py
```

Result: **40 passed**. Changed Python modules pass Ruff; whitespace checks pass.
Coverage includes portable composition loading, physical-unit global metrics,
finite/exact prediction coverage, declaration identity, fixed loss populations,
agent-selected training fractions, frozen stage parameters, write-once clocks
and checksummed read-only inputs. This is targeted validation, not a full-suite
claim.

Two newly allocated H100s ran the native train/export/infer/score path twice,
with 128 training examples and one epoch per attempt:

| Task | Epoch-loss rows | Formal rows | Training wall seconds | Inference seconds | Scoring seconds |
|---|---:|---:|---:|---:|---:|
| LIGO | 9,000 | 90,000 | 5.88 / 3.56 | 5.01 / 4.96 | 2.14 / 2.14 |
| Project 8 | 500 | 5,000 | 5.72 / 3.50 | 2.74 / 2.76 | 1.89 / 1.82 |

Exported-model loss agrees with the training receipt on the same fixed subset;
global RMSE agrees with independent computation. These timings are tiny-model
qualification measurements, not throughput estimates for agent-selected models.

Both hosts also ran real OpenAI agent qualification for at most 720 seconds.
Each completed a generated model's Trial and Formal with valid full-population
scores, entered iteration 2, and restored the previous model and incumbents.
The deadline then stopped each run (exit 124); **neither completed two entire
proposal iterations**. This proves first-iteration execution and cross-iteration
handoff, not two complete scientific explorations or good model performance.
Short budgets triggered normal time-admission rejection and subsequent recovery.
LIGO literature requests encountered public S2 rate limiting; the node completed
with zero findings and the workflow proceeded. Project 8 retrieved ten papers.

## Findings corrected before release

- The first real launch refused contradictory qualification settings: a finite
  phase timeout with the runtime watchdog disabled. Qualification now enables
  the watchdog in memory. Frozen formal workflow files are not shortened.
- Review found RMSE configured as primary despite the plan selecting R2. Both
  compositions now maximize global R2, with physical RMSE secondary. Native
  scoring was replayed on existing predictions over all 90,000/5,000 rows;
  R2 matched independent calculations. No retraining was needed. Rankings are
  equivalent for the same fixed population, but metric identity is now explicit.
- An operator replay initially omitted the training member of the transported
  scope bundle. Native scoring refused it. The complete bundle replay passed;
  this was a diagnostic harness error, not a task/runtime patch.

Real root-supervisor tests on both hosts used a four-second clock and a non-root
worker. The worker could write its workspace but could not read/change the
clock, read the credential file, or write framework source. Deadline stops took
3.55/3.15 seconds (integer-second clock); resuming preserved the original clock
and did not restart expired work. No provider call was needed for these tests.

## Boundaries

These NoPrior workflows disable human advice and Data Analysis; dynamic
Literature Review remains enabled. Training pools are full; each agent chooses
its training fraction. Epoch loss uses frozen 10% validation; Formal uses 100%.
The 100-epoch ceiling does not impose the student's 20-epoch recipe. LIGO has
16 GB and 10/30 minute Trial/Formal budgets within 12 hours; Project 8 has
40 GB and 30/120 minute stage budgets within 24 hours.

The native fixed-workflow evaluator/trainer account can materialize validation
targets. This is not the external-orchestrator private-worker isolation service
and does not prove resistance to arbitrary malicious generated Python. Task
Health is explicitly absent; finite outputs and exact coverage are mandatory.
No offline test scores or baseline reproduction are claimed. Per-SNR and MAE
analyses, if performed later, are operator reporting rather than live selection.

Qualification artifacts are collected separately and must be physically removed
before formal start. Formal deployment records own actual release tags, host
identities, immutable start/deadline, collection checks and run health.
