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

## Frozen study choices

- Energy-matching bins: `[0, 100, ..., 3600]` keV.
- Split identity: `(process, ev_no)`, hashed once into 80/10/10 partitions.
- Training imbalance treatment: positive weighting in BCE; no event is moved
  across a partition and no test event participates in model selection.
- Tracker representation: pointwise one-dimensional convolutions followed by
  masked symmetric pooling. This treats tracker hits as a variable-length set
  rather than assigning scientific meaning to their stored row order.
- Missing `tR`: zero imputation plus an explicit missingness channel.
- Final runtime comparisons are measured in isolation. Concurrent exploratory
  runs may be used only to choose the configurations worth measuring.

The 100-keV bin width was selected after a validation-partition sensitivity
check at 25, 50, 100, 200, and 400 keV. Widths from 25 through 200 keV retained
essentially the same common energy support; 100 keV avoids unnecessarily sparse
bins without erasing the spectrum structure. This choice is frozen before any
baseline score is examined.
