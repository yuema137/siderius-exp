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

- Energy-matching bins: `[0, 25, ..., 3600]` keV.
- Split identity: `(process, ev_no)`, hashed once into 80/10/10 partitions.
- Training imbalance treatment: deterministic, without-replacement selection
  of equal signal and background counts inside every fixed 25-keV energy bin.
  Bins lacking either class do not enter training. Selection happens only
  inside the fixed training partition; no event moves across a partition and
  no test event participates in model selection.
- Tracker representation: pointwise one-dimensional convolutions followed by
  masked symmetric pooling. This treats tracker hits as a variable-length set
  rather than assigning scientific meaning to their stored row order.
- Missing `tR`: zero imputation plus an explicit missingness channel.
- Final runtime comparisons are measured in isolation. Concurrent exploratory
  runs may be used only to choose the configurations worth measuring.

The 25-keV bin width was selected before the balanced baseline matrix after a
validation-partition sensitivity check at 5, 10, 20, 25, 50, 100, and 200 keV.
The energy-only residual AUC was 0.50030 at 25 keV, compared with 0.50109 at
50 keV, 0.50426 at 100 keV, and 0.51643 at 200 keV. The complete validation
partition retained 114 common bins and effective weight for 46,456 events per
class at 25 keV; the median common count was 165 events per class per bin.
Finer 5- and 10-keV grids reduced the already negligible residual but left many
tail bins with only a few events. The 25-keV rule therefore controls residual
energy leakage without paying unnecessary sparse-bin variance. It is frozen
before any energy-balanced baseline score is examined.
