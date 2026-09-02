# SuperNEMO qualification record — 2026-09-02

## Exact pair

- SIDERIUS: `7568fc54b6bcc00ce6ee5c1e88f3219550a688cb`
- siderius-exp: `66c99cacda9c9597ada7e6a6df0cbff154258726`
- TestPod workspace: `/workspace/supernemo_runs/qualification_66c99ca_7568fc54`

## Result

The first real two-iteration launch failed before training. The qualification
profile declared one round while the chain forces the final round to Formal.
Consequently its Trial-scoped overrides could apply to zero rounds, and
`HyperparamTuningInput` correctly refused the contradictory plan. Iteration 2
then correctly refused to restore state from iteration 1's failed manifest.

Classification: experiment configuration failure, not an infrastructure bug
and not a scientific invalidation. The generic fail-closed framework behavior
was correct.

The profile now declares two rounds: one Trial round followed by the forced
Formal round. A launcher regression asserts both scopes remain present. The
failed workspace is retained as evidence; the rerun must use a fresh identity.

## Corrected-profile rerun

The corrected profile reached real H100 execution at exact pair SIDERIUS
`7568fc54b6bcc00ce6ee5c1e88f3219550a688cb` and siderius-exp
`c4cca63517ef7d00719281f303fd0389b58887f3`. Its first Trial exposed generic
SIDERIUS issue #420: measured admission timed GPU optimizer computation only,
excluding task-owned DataLoader latency. It predicted 16.9298 seconds for 576
steps and admitted the 60-second budget; actual training took 154.6803 seconds,
a 9.1366x underprediction. The rerun was stopped after preserving its runtime
record. Qualification remains incomplete pending a generic framework repair.

## Generic repair witness

SIDERIUS pull request 421 (`2c818e12`) moves the measured optimizer-step wall
clock ahead of task-owned batch acquisition. A fresh TestPod run used the same
external SuperNEMO composition at exact pair SIDERIUS `2c818e12` and
siderius-exp `c4cca635`, workspace
`/workspace/supernemo_runs/qualification_c4cca63_2c818e12_b`.

The first candidate measured a steady median of 645.6681 ms over ten optimizer
steps, including task-owned loading, host-to-device transfer, and optimizer
compute. It projected 371.9048 seconds for 576 training steps and a known-cost
lower bound of 376.9550 seconds including setup. The measured admission layer
therefore refused the 60-second Trial budget after 12.8074 seconds of setup and
verification work. A later candidate failed to establish steady state within
the bounded verifier and was also refused fail-closed. The witness was stopped
after the generic acceptance property was established; it is not a completed
task qualification and its workspace is retained as non-authoritative repair
evidence.

## Loader-aware merged-SHA rerun

A fresh TestPod run used SIDERIUS
`6bcdeb2f55b47ced6bcadaa08ddfd88875964261` and siderius-exp
`16a0823afd78ca014444a34730c04ebfda30a45c` in workspace
`/workspace/supernemo_runs/qualification_16a0823_6bcdeb2f_run1`.

The repaired measured-admission path behaved correctly. Three executable
candidates were refused after real setup and training verification projected
known-cost lower bounds of 572.4, 380.7, and 313.2 seconds against the
one-minute Trial budget. No rejected attempt wrote an experiment result. A
planner proposal using a non-snapshot selection strategy was independently
refused by the task-owned deterministic-snapshot contract; the subsequent
proposal consumed that feedback and returned to snapshot selection.

The run established that the original qualification scope was too large for a
dense 3D candidate: 5% scope with a 10% per-epoch subsample materialized about
37,000 training events. It was stopped after the evidence was recorded. The
qualification profile now uses 1% scope with a 1% per-epoch subsample for both
Trial and Formal training, while retaining 1% evaluation. Campaign portions
are unchanged. A fresh workspace is required for the rerun.

## Completed bounded qualification

A fresh TestPod run completed at exact pair SIDERIUS
`6bcdeb2f55b47ced6bcadaa08ddfd88875964261` and siderius-exp
`9719616dcfc8dc7d80a6946d6ce67b56a4c88b84`, workspace
`/workspace/supernemo_runs/qualification_9719616_6bcdeb2f_run2`. The launcher
exit code was zero and both iteration manifests have status `completed`.

Iteration 1 completed one Trial and one Formal round. The valid Trial score was
`0.5857041215372332`; the valid Formal score was `0.6231508552021149`.
Iteration 2 restored the prior plugin, proposal, Trial incumbent, and verified
Formal incumbent. Its interpretation consumed both prior experiment records
and produced a new proposal. The first proposed configuration used batch size
64, which could not form one full resource-probe batch from the deliberately
small qualification scope. The preflight refused it before training. The agent
consumed that failure, reduced the batch size to 8, and completed valid Trial
and Formal rounds with scores `0.6098216066481994` and
`0.5892530294988616`, respectively.

All four successful experiment records declare `energy_matched_roc_auc` as the
higher-is-better golden metric and `ordinary_roc_auc` as secondary evidence.
Both iterations used the same task-composition fingerprint, Health policy hash,
Literature Review configuration hash, measured Trial/Formal admission mode,
and 1% evaluation scope. Each manifest records real Formal evidence and valid
Trial/Formal incumbents. The one rejected attempt is a correctly recorded
resource refusal, not an infrastructure failure or scientific invalidation.

The chain emitted warnings while looking for an iteration-1 interpretation
digest during iteration-2 resume. This is a non-blocking observability edge:
iteration 1 has no previous result to interpret, while iteration 2 created its
own interpretation from iteration 1's two records and demonstrably consumed
the restored state. No continuity evidence is missing from the completed run.

Qualification verdict: PASS for the bounded external-consumer workflow. This
run establishes execution and continuity, not scientific performance. The
20-iteration campaign must use a fresh workspace and the documented campaign
profile; it must not resume from this qualification identity.
