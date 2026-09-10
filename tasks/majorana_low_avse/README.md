# Majorana Demonstrator Low-AvsE classification

This task uses the labeled subset published in Zenodo record 8257027. One
sample is one 3,800-value `raw_waveform`; the binary target is
`psd_label_low_avse`. The model receives no energy, identifier, detector, run,
timing, target, or alternate-PSD field.

The official 16 Train files and 6 Test files are independent supervised
partitions. The three unlabeled NPML files are never used for training or
scoring. Within each fixed 25-keV `energy_label` bin, the task data path selects
equal numbers from both classes. Energy is task-owned matching metadata, not a
model feature. The golden metric is energy-matched ROC AUC; ordinary ROC AUC is
observational only.

The task applies one explicit waveform transform: subtract the mean of the
first 500 samples and divide by their standard deviation, floored at one ADC
unit. `tp0` is not used.
