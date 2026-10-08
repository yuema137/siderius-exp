# SuperNEMO signal-background classification

This task classifies simulated SuperNEMO Demonstrator events as neutrinoless
double-beta signal (`0nubb`) or background (`2nubb`, `Bi214`, `Tl208`). One ML
sample is one physical event, not one HDF5 row. Rows sharing the same `ev_no`
within one process file are tracker hits belonging to the same event.

## Start with the tutorial

Follow the [SuperNEMO notebook and setup guide](../../tutorials/supplementary/supernemo/README.md)
to prepare data, create an external project, change parameters and run a
three-iteration demo through its saved script. The guide includes a recorded
example and explains where your own results appear. This is a process demo,
not a paper artifact or a promise of a high score.

## Scientific contract

- Event inputs: `E1`, `E2`, `dY`, `dZ`, and `phiR`.
- Tracker-hit inputs: the variable-length collection of `tX`, `tY`, `tZ`, and
  `tR` rows associated with the event.
- Model tensor: float32 `[224, 11]`; events with more than 224 hits are
  truncated, and shorter events are zero-padded. Valid-row and missing-radius
  flags distinguish padding and missing values. The
  [forward contract](declared/task_config.yaml) defines the channels.
- Forbidden inputs: `theta` and `phiS` are simulation-truth quantities;
  `ev_no` is an identity field. None may reach a classifier.
- Target: `0nubb = 1`; every released background process equals `0`.
- Golden metric: deterministic energy-matched ROC AUC, measuring how well
  signal ranks above background; higher is better.
- Training objective: cross entropy on two logits (`ce`, reduction `mean`).
- Data cuts: no energy-window or TPP-separation cut is introduced implicitly.

The energy-matching ruler uses fixed 25-keV bins from 0 through 3,600 keV.
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

## Local-code declaration

[`compositions/signal_background.yaml`](compositions/signal_background.yaml)
declares `code_package.root: ../plugins` with exactly five Python members:
`_supernemo_task.py`, `_supernemo_data.py`, `_supernemo_metrics.py`,
`energy_matched_auc.py`, and `supernemo_reference_pointnet.py`. Relative imports
share the helper-defined scope between the data path and both metric adapters;
the required model is part of the same captured identity.

The composition keeps CE/mean, explicit no-Health, the 25-keV energy-matched
primary AUC, ordinary secondary AUC, and fixed model geometry unchanged.
Use the [paired environments](../../README.md#framework-revision) and a fresh
workspace after changing declared code. The framework checks all captured
members in cold children; a missing or changed helper must be restored to its
pin, not bypassed with a global module alias or source-path overlay.
