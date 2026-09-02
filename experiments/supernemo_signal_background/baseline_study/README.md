# SuperNEMO baseline and resource study

This bounded study establishes the data representation, fixed
energy-matching rule, baseline model behavior, and measured resource envelope
before a SIDERIUS discovery experiment is configured.

The study must record:

- exact dataset checksums and event-level split receipts;
- fixed energy-matching bin edges and common-support coverage;
- MLP, CNN, and ResNet-style baseline definitions at reviewed capacities;
- training and validation loss curves;
- energy-matched ROC curves and AUC values;
- parameter count, batch size, throughput, wall time, and peak VRAM;
- isolated timing separately from any concurrent exploratory execution;
- evidence-backed recommendations for Trial/Formal portions and resource
  budgets.

The held-out test partition is not used for model selection in this study.
Raw data and runtime artifacts live in the configured workspace, not in Git.

