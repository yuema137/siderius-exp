# SuperNEMO signal-background classification

This task classifies simulated SuperNEMO Demonstrator events as neutrinoless
double-beta signal (`0nubb`) or background (`2nubb`, `Bi214`, `Tl208`). One ML
sample is one physical event, not one HDF5 row. Rows sharing the same `ev_no`
within one process file are tracker hits belonging to the same event.

## Scientific contract

- Event inputs: `E1`, `E2`, `dY`, `dZ`, and `phiR`.
- Tracker-hit inputs: the variable-length collection of `tX`, `tY`, `tZ`, and
  `tR` rows associated with the event.
- Forbidden inputs: `theta` and `phiS` are simulation-truth quantities;
  `ev_no` is an identity field. None may reach a classifier.
- Target: `0nubb = 1`; every released background process equals `0`.
- Golden metric: deterministic energy-matched ROC AUC, higher is better.
- Training objective: binary cross entropy.
- Data cuts: no energy-window or TPP-separation cut is introduced implicitly.

The energy-matching bin edges and weighting rule are task-owned and fixed
before qualification. Agents may not alter the metric definition.

## Split invariant

The unique identity is `(process, ev_no)`. A deterministic hash assigns each
identity to train, validation, or test with an 80/10/10 target ratio. Every hit
from one event follows that event into exactly one partition. Trial and Formal
select different deterministic portions inside the same fixed partitions; they
never derive new splits. Test identities remain unavailable to training and
model selection.

Raw HDF5 files and generated indexes remain in an operator-supplied data
directory outside the repository.

