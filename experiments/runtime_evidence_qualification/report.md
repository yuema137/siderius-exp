# Runtime evidence qualification for issue 567

## Scope and revisions

Final reviewed infra: `7c3b4031a6930f5fe753a88dfccc07e6abc1b727`.
The original four fixed-model runs used infra `d0f5b5bc`; their eight saved
training/validation traces were replayed on the final revision without retraining.
The four fixed-model runs used exp `ea2e40b`; subsequent exp changes contain
consumer test fixtures and this evidence, not scientific execution changes.
This is runtime-mechanism qualification, not a supplementary tutorial, a Health
qualification, an accuracy comparison, or paper artifact retraining.

The candidate uses retained steady elapsed time and actual remaining observation
capacity for its fallback. Before acceptance, a distribution-block check retains
observed upper support and distinguishes recurring expensive units from a
separated slower regime. The existing plateau-based slowdown guard remains
unchanged. Count evidence comes from the same window that supplies the prediction. Infra has no task- or GPU-specific branch.

## Real workloads

All four launches completed on a local RTX 5090, using existing data and fixed
reference CNNs. API calls and cost were zero. Each launch had a 300-second
training budget and a whole-process limit of 450 seconds including cleanup;
the supervisor reserved 15 seconds for descendant cleanup. The aggregate limits
were four launches, 30 GPU minutes and 45 wall minutes, including failed starts
and retries. There were no failed launches or retries.

| Case | Materialized training samples | Validation samples | Epochs | Training observations / retained | Validation observations / retained | Whole-process seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MJD small | 64 | 64 | 64 | 151 / 146 | 100 / 100 | 31.31 |
| MJD larger | 1024 | 512 | 16 | 156 / 100 | 109 / 100 | 16.09 |
| Pet small | 64 | 64 | 64 | 21 / 17 | 21 / 17 | 30.91 |
| Pet larger | 2946 | 400 | 16 | 18 / 15 | 16 / 16 | 108.00 |

Both phases verified in every case. MJD small validation and both larger MJD
phases used the distribution fallback; the other phases used the ordinary
rolling detector. Batch size was 16. Pet larger materialized 2946 rows and ran
184 optimizer steps per epoch under the declared loader behavior; do not infer
that every materialized row contributed a gradient. MJD validation uses its
existing official Test split as feedback, not an untouched final holdout.

Total supervised wall time was 186.31 seconds. Treating each process's entire
lifetime as GPU occupancy gives the conservative upper bound of 186.31 seconds
(3.11 minutes), not a measurement of active GPU kernels. Another user's GPU
process existed at preflight and was left untouched; these are shared-hardware
functional witnesses, not exclusive performance benchmarks.

[evidence.json](evidence.json) records actual scopes, model/training settings,
runtime policies, both phases' raw rates and physical observation durations,
composition fingerprints, result hashes and admission outcomes. Full local
workspaces, selected sample identities and the supervisor ledger are retained
with the operator. No dataset was downloaded again. No earlier timing trace was
repeated to manufacture extra observations.

## Offline checks and historical presentation

- 157 targeted infra tests passed, including actual next-planner propagation for
  budget excess, insufficient evidence and missing historical cause codes.
- The mutation removing the distribution-block guard failed all ten slowdown
  controls. Original successful recorded traces retain their outcomes and
  measured medians; truly short traces remain unverified.
- All 47 declared rendering comparisons match in
  [prompt-evidence.json](prompt-evidence.json). Four captured paper planner
  startups match their original hashes in [planner-startups.json](planner-startups.json).
  The separate LIGO-derived planner branch check matched its 12 frozen pairs.
- Six existing planner provider identities remain unchanged. Explicit v5
  providers project the new refusal format to the historical wording without
  modifying stored records. The producer fixture was captured at the candidate
  infra revision; infra owns producer propagation tests and exp owns its
  consumer projection tests, avoiding a permanent private-node import in exp.
- Prompt compatibility 0.2.0 explicitly qualifies the changed schema assembly
  and retains the original qualified assembly. Unknown assemblies are refused.
  Its source-bound profile identity changes, so use a new workspace. Existing
  locks retain package 0.1.0 and their original exp revision.

These checks cover declared inputs and branches, not every historical
conversation or nondeterministic model reply. Runtime execution keeps corrected
behavior; compatibility restores presentation only. Public infra remains pinned
to `e800fc1f` until a release is separately selected. No public synchronization
or merge is implied by this report. Pre-existing full-suite failures tracked in
infra issue 606 are outside this selective qualification.

## Expanded paper and robustness audit

After the operator requested a second audit, the committed production verifier
was run against the full 1247-case offline matrix, not only the prototype.
The final repair was rerun on all 1247 inputs. It retains all original/Pet
success outcomes and medians; all declared sustained-shift controls are refused.
Refusal timing can differ from the initial candidate. The matrix includes
600 stationary heterogeneous traces, 600 controlled slowdown traces across six timing scales,
the original traces and saved Pet/MJD phases, short workloads and dimensional
controls. The 18 baseline-pass/candidate-refusal cases are three pre-existing
false-acceptance slowdown seeds at six scales, not stationary regressions.
Seed/scale variants are related controls, not independent scientific trials.

A separate read-only replay covered 929 archived paper phases from the verified
source inventory: TESS 134, LIGO 107, Project8 75, TIDMAD 613 (NoPrior and analysis-on,
all four bands). Every phase supplied explicit physical durations. With the
same recorded inputs, pre-PR infra verified 860 phases; the candidate verified 868.
None of the 860 previously verified phases became a refusal. Eight TESS phases
now verify instead of exhausting evidence. Three already-successful phases
(one TESS, two TIDMAD) verify earlier and obtain different timing medians.
The detailed differences are in [paper-runtime-comparison.json](paper-runtime-comparison.json).

This establishes no new false refusal on these recorded successful phases. It
does **not** establish unchanged fresh runtime predictions, admission margins
or downstream trajectories: changed medians can change future predictions.
Historical prompt reproduction uses the archived inputs through the explicit
exp profiles. It does not silently replace fresh measured values with historical
ones or reinstate incorrect runtime rules in infra.

The exact per-task overlays are retained in
[paper-runtime-v5.json](../shared/planner_compat/profiles/paper-runtime-v5.json).
All four captured paper startups also match when using these **new v5**
selectors, as recorded in [planner-v5-startups.json](planner-v5-startups.json).
The separate analysis-on profile retains its previously qualified retry policy.

## Independent review and repairs

Independent review initially found a production blocker: retaining a minimum
median from short windows falsely refused an unchanged repeating mixed-rate
workload. It also reproduced stationary bimodal and lognormal regressions.
That implementation was replaced, not waived. A fresh independent reviewer
then found a missed genuine slowdown outside the initial seed set. Requiring
a stable earlier plateau conflated two questions: whether earlier rates were
observed, and whether they could supply a stable prediction. That unnecessary
reference-stability condition was removed before merge.

The final guard uses the first sufficiently long observation window without a
pathological upper tail, retaining contiguous preceding ordinary observations.
It compares complete observed blocks using their support and medians before
acceptance. It adds no task-specific rules, hardware constants, numeric policy
or historical execution mode. Existing plateau, observation, time and budget
checks remain in force. [independent-review.md](independent-review.md) records
the resolved findings and separate final review verdicts.

Final production checks add 2,000 stationary comparisons with no new
baseline-success refusal and 900 sustained-shift controls across scales and
warmup conditions. A fresh reviewer also tested 1,000 further shifted traces,
1,000 stationary traces and 3,000 recurring patterns without a new defect.
These families overlap conceptually and are not independent scientific trials.
[repair-evidence.json](repair-evidence.json) retains the bounded results and
[final-planner-identities.json](final-planner-identities.json) verifies all six
old provider identities remain unchanged. All 47 historical rendering pairs,
four actual v5 startup captures, 929 paper phases and eight saved fixed-model
phases were checked again on the final infra revision.

The exp adapter now rejects explicitly contradictory admitted cause codes and
pre-launch stages before converting a marked refusal. Twenty-five tests in each
environment include fully stamped typed history, permitted missing causes and
legitimate post-phase/allocation refusals. No raw history is normalized to bypass
validation. The v5 content identity changes; use a new workspace as documented.

All review repairs and final checks used zero additional API calls or GPU runs.
The original real-training and live-planner observations below retain their
actual source revisions. They were not rerun or represented as final-head live
execution. Matching archived messages does not guarantee fresh LLM outputs,
weights, trajectories or every missing historical conversation.

## Live planner feedback observations

The operator subsequently authorized two OpenAI `gpt-5.6-sol` calls, capped at
$2 and 600 seconds, with no GPU use and no additional retries. Both completed
in 37.08 seconds. Conservative accounting totals $0.151720; this includes a
cache-write allowance and applies no cache discounts, so it is not an invoice.
The request hashes, response hashes, token counts and complete validated plans
are recorded in [planner-response-evidence.json](planner-response-evidence.json).
No raw dataset or credential file was sent.

Both requests used the current planner with captured TESS task/model context
and explicitly synthetic refusal histories. For `verification_failed`, the
planner recognized that an unstabilized runtime estimate provides no evidence
for changing the architecture or hyperparameters; it retained the 40-epoch
proposal. For `budget_exceeded`, it cited the 420-second forecast against the
300-second budget and proposed 20 epochs. Both responses passed
`ExperimentPlan` validation, selected the required final-round Formal role,
kept full training/evaluation scope, and stayed below the 100-epoch role cap.

These two observations support the narrow conclusion that the returned answers
distinguished the causes. They do not establish reliable future behavior or
improvement over the old prompt. The budget-excess answer also changed target
standardization and checkpoint selection. Cooperative execution can continue
beyond proposed epochs within its role cap and budget, so the smaller epoch
proposal does not prove a shorter executed workload or successful admission.
Neither plan was trained; no runtime, VRAM or scientific-score claim follows.
This check is separate from historical paper prompt reproduction.
