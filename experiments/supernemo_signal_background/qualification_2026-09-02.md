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
