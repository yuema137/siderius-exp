# Majorana Demonstrator Low-AvsE classification

This task uses the labeled subset published in Zenodo record 8257027. One
sample is one 3,800-value `raw_waveform`; the binary target is
`psd_label_low_avse`. The model receives no energy, identifier, detector, run,
timing, target, or alternate-PSD field.

## Start with the tutorial

Follow the [MJD notebook and setup guide](../../tutorials/supplementary/mjd/README.md)
to prepare data, create an external project, change parameters and run a
three-iteration demo through its saved script. The guide includes a recorded
example and explains where your own results appear. This is a process demo,
not a paper artifact or a promise of a high score.

## Scientific contract

The official 16 Train files and 6 Test files are independent supervised
partitions. **Official Test serves as workflow validation:** its scores feed
model search. This tutorial has no additional untouched final-test partition.
The three unlabeled NPML files are never used for training or scoring. Within each fixed 25-keV `energy_label` bin, the task data path selects
equal numbers from both classes. Energy is task-owned matching metadata, not a
model feature. The golden metric is energy-matched ROC AUC; ordinary ROC AUC is
observational only. AUC measures how well the model ranks events that pass the
Low-AvsE cut above events that fail it; higher is better. These are the released proxy labels,
not ground-truth signal/background identities.

The task applies one explicit waveform transform: subtract the mean of the
first 500 samples and divide by their standard deviation, floored at one ADC
unit. `tp0` is not used.

## Local-code declaration

[`compositions/low_avse.yaml`](compositions/low_avse.yaml) declares
`code_package.root: ../plugins` with exactly `_majorana_task.py`,
`_majorana_data.py`, `_majorana_metrics.py`, and `majorana_reference_cnn.py`.
The data and metric adapters import their shared scope through ordinary
relative imports. The required model belongs to the same finite captured set.

This acquisition route preserves the composition's CE/mean objective, explicit
no-Health, 25-keV matching, both AUC metrics as higher-is-better, and
3,800-sample geometry.
Keep the [two environments on the exact pin](../../README.md#framework-revision).
An intentional member edit changes implementation identity and requires a fresh
workspace; restore accidentally changed pinned files instead of rewriting an
old lock or relying on parent-process modules or `PYTHONPATH`.
