# Independent review and resolution

## Final reviewed source

Infra: `7c3b4031a6930f5fe753a88dfccc07e6abc1b727`.
Exp code repair: `ea4dc96` (the subsequent evidence commit changes reports only).
Independent agents reviewed code separately from the implementing agent.
The final infra reviewer did not design or implement the repair.

## Findings resolved before merge

1. **P1, infra:** A minimum median selected from short windows forgot recurring
   expensive observations. A repeating mixed-rate workload verified at step 100
   on the base but was falsely refused at step 20 on the initial candidate.
   Stationary bimodal and lognormal regressions also reproduced. The minimum
   reference state was removed. A pure observed-distribution helper now checks
   full blocks before acceptance while preserving the original plateau guard.
2. **P1, first repair:** A separate reviewer found a genuine 15x shift at seed
   163 which base infra refused at step 206 but the first repair accepted at
   step 196. Earlier-window stability was incorrectly required to establish
   observed support. Removing that requirement preserves prediction stability
   checks while detecting the disjoint historical rate regimes. The exact
   counterexample, with and without warmup, is now in the regression suite.
3. **P3, exp:** The new historical view accepted explicit admitted cause codes
   and a pre-launch stage alongside a marked in-subprocess rejection. The
   adapter now refuses these contradictions. Valid missing causes and
   post-phase/allocation refusals retain their historical messages. Tests use
   fully stamped typed records through the composed providers. No malformed
   historical data is silently normalized.
4. **Readability, exp:** The ordered setup now distinguishes archived v4 input
   replay from v5 consumption of newly produced factual refusal records before
   the configuration table, rather than leaving the condition until the end.

## Final independent verdicts

The exp reviewer approved the narrow repair after 25 tests and installed-source
verification. The final infra reviewer approved the exact source revision after
157 targeted tests and independent out-of-sample timing controls: 1,000 shifted
traces, 1,000 stationary uniform traces and 3,000 recurring patterns. Scaling
checks included factors 1e-6 and 1e6. No remaining merge-blocking source defect
or maintenance concern was identified within this scope.

The implementing agent subsequently completed the required final-revision
checks: 929 archived paper phases, 47 historical rendering comparisons, four
v5 paper startups, eight saved fixed-model training/validation phases, and
explicit identity checks for all six existing planner providers. See
[repair-evidence.json](repair-evidence.json) and the linked receipts in
[report.md](report.md). Deleting the new guard causes all ten targeted slowdown
controls to fail, so these checks exercise a real decision boundary.

## Boundaries

No new API or GPU execution was used during review repairs. The earlier four
real training runs and two real planner calls retain their original revision
receipts. Final revision qualification of those timing inputs is offline.
Full-suite CI is not claimed green; pre-existing failures remain in infra #606.

Finite observed inputs do not prove universal distribution-shift detection.
Overlapping support may be inconclusive, rare tails can mislead finite samples,
and changes after verification are unknowable from the preceding trace.
Correct execution defaults remain in infra. Historical scientific inputs,
settings and prompt views remain in exp; supplied-message parity does not
promise identical fresh stochastic replies, model weights or trajectories.
