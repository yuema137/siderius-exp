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

The energy-matching ruler uses fixed 100-keV bins from 0 through 3,600 keV.
Within every bin containing both classes, signal and background each receive
total weight equal to the smaller class count. Bins without both classes are
excluded and their coverage is reported. This deterministic weighting removes
the energy-spectrum population shortcut without random downsampling. The
edges and weighting rule are task-owned; agents may not alter them.

The released tracker-radius column contains a small number of `NaN` values
(0.41--0.60% depending on process). Tracker models replace a missing `tR` with
zero before standardization and receive a separate missingness indicator. No
other non-finite tracker values were observed in the complete scan.

## Split invariant

The unique identity is `(process, ev_no)`. A deterministic hash assigns each
identity to train, validation, or test with an 80/10/10 target ratio. Every hit
from one event follows that event into exactly one partition. Trial and Formal
select different deterministic portions inside the same fixed partitions; they
never derive new splits. Test identities remain unavailable to training and
model selection.

Raw HDF5 files and generated indexes remain in an operator-supplied data
directory outside the repository.
