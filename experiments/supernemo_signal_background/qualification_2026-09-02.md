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
