# Majorana qualification record — 2026-09-02

The task package passed exact-pin composition, split, model-forward, launcher,
energy-balance, metric, and dataset-integrity checks. A real qualification was
started at SIDERIUS `7568fc54b6bcc00ce6ee5c1e88f3219550a688cb` and
siderius-exp `11d51dd33a245c9a2a56e4ddf52fa2a49b5b5cf2` after all 22 supervised
files passed the task-owned size and MD5 gate.

The run was stopped during iteration 1 literature review when the concurrent
SuperNEMO external witness proved generic SIDERIUS issue #420. The shared
measured-admission timer excluded task-owned DataLoader latency, so continuing
Majorana against that framework revision could not establish valid resource
qualification. The workspace is retained as non-authoritative evidence; the
next run must use a fresh identity and the repaired exact SIDERIUS revision.

## Loader-aware two-iteration run

A fresh run used SIDERIUS
`6bcdeb2f55b47ced6bcadaa08ddfd88875964261` and siderius-exp
`16a0823afd78ca014444a34730c04ebfda30a45c` in workspace
`/home/klz/Data/SIDERIUS_EXP/qualification/majorana_low_avse_16a0823_6bcdeb2f`.
Iteration 1 completed valid Trial and Formal rounds with energy-matched ROC AUC
scores `0.8776060862345885` and `0.8877503769698174`. The official Train/Test
split remained disjoint and every selected 25-keV energy bin contained equal
signal and background counts.

Iteration 2 restored the verified Formal incumbent and completed a valid Trial
at `0.8487486797217398`. Its Formal round did not execute: fifteen measured
admission attempts projected known-cost lower bounds of approximately 62--66
seconds against the qualification's 60-second Formal budget. The records show
zero VRAM-gated or other failure attempts. This is a correct resource refusal
caused by an overly narrow qualification budget, not an infrastructure failure
or scientific invalidation. The iteration manifest is top-level `completed`,
but its workflow status is `partial`, with one completed round and
`has_formal_evidence=false`; it is therefore not accepted as a completed
two-iteration qualification.

The qualification treatment now keeps its one-minute Trial budget and raises
only its Formal budget to two minutes. Campaign budgets remain unchanged at
10 minutes for Trial and 30 minutes for Formal. A fresh exact-SHA workspace is
required for the rerun.

## Corrected two-minute Formal qualification

The fresh rerun used SIDERIUS
`6bcdeb2f55b47ced6bcadaa08ddfd88875964261` and siderius-exp
`ef264e05a6bc746d3b768c8a8118f7b4bd4343d4` in workspace
`/home/klz/Data/SIDERIUS_EXP/qualification/majorana_low_avse_ef264e0_6bcdeb2f_v2`.
Both iterations completed two rounds and produced real Trial and Formal
evidence under measured admission. Iteration 1 selected a best valid Trial
energy-matched ROC AUC of `0.49331820632987017` and a best valid Formal score
of `0.5499512683191314`. Iteration 2 consumed the first iteration's persisted
state and selected a best valid Trial score of `0.49150936716816285` and a best
valid Formal score of `0.5104347813453858`.

The second iteration contains six attempt records, five Formal records, and one
successful Formal record. Its manifest reports `status=completed`, two
completed rounds, and `has_formal_evidence=true`. Together with the first
iteration's completed manifest, this satisfies the bounded two-iteration
external-consumer qualification. These scores are mechanism evidence from a
one-epoch, deliberately small-scope qualification; they are not scientific
campaign results.
