# PROVENANCE — `phyts_tess`

## Source

PhyTS, *A Benchmark for Scientific Time Series* (NeurIPS 2026 submission),
TESS subset. Data published at Hugging Face `PhyTS-team/PhyTS-bench`; the
benchmark's own code is at `github.com/kyoon-mit/PhyTS`.

Upstream of PhyTS: light curves extracted by the TESS–Gaia Light Curve
pipeline (TGLC) from the TESS Primary Mission and first Extended Mission;
labels build on the TESS variable-star catalog, and the near-core rotation
frequencies follow the asymptotic methodology of Aerts et al. (2025), which
was calibrated on a restricted stellar-mass range.

This package covers **Task B only** — near-core rotation regression on the
`GDOR_SPB` subset. Task A (eight-class variability classification) is not
packaged.

## Committed identity

`data/manifests/rotation_identity.csv`, sha256
`b03b8872943b696ab3dc7a63a8579f5dec379c2bc0562ab1c613122e3cea50ad`,
3,780 rows derived on 2026-09-20 from the released
`tess_regression_{train,val}.parquet`.

Source files as received, 2026-09-20:

| file | rows |
|---|---|
| `tess_regression.parquet` | 4,183 |
| `split/tess_regression_train.parquet` | 3,338 |
| `split/tess_regression_val.parquet` | 442 |
| `split/tess_regression_test.parquet` | 403 (never staged, never committed) |

Schema as received: `GaiaID int64, TIC int64, sector int64, frot double,
frot_err double, time list<double>, flux list<double>` — matching the
paper's Table 5.

## Verified against the data, not the paper

**Splits are 80/10/10 grouped by `GaiaID`, with zero overlap** in all three
pairwise comparisons. This matches paper §3.2 and not appendix D.2, which
describes a 70/15/15 re-split grouped by TIC — that appendix split belongs to
the paper's own foundation-model probing experiment, not to the released
artifact.

**`(GaiaID, sector)` is unique in every split. `(TIC, sector)` is NOT unique
in train**, so the TESS Input Catalogue identifier is carried for provenance
and never used as a key.

**Light-curve length is variable and bimodal**: 542 minimum, 1124 median,
3917 maximum. The clusters near 1.0–1.2k and 3.5–3.9k are the 30-minute
Primary Mission and 10-minute first Extended Mission cadences. The frozen
1024-sample window is PhyTS appendix D.2 parity, not an optimum, and it
truncates most Extended-Mission curves.

## Three properties of the targets that affect interpretation

**1. `frot` is derived per light curve, not per star.** 455 of 505 training
stars carry more than one distinct target value across their sectors. Since
splits are grouped by star this causes no leakage, but it puts a label-noise
ceiling on achievable R-squared:

| split | target variance | within-star variance | ceiling if the per-star mean were predicted perfectly |
|---|---|---|---|
| train | 0.47977 | 0.04017 | R-squared 0.9163 |
| val | 0.31566 | 0.00748 | R-squared 0.9763 |

The PhyTS baselines reach 0.665, so the ceiling is not currently binding.

**2. 26 of 4,183 rows carry a negative `frot`, and 23 of them are the exact
repeated constant `-0.271916` with `frot_err` exactly `0.038500`.** That
value sits about 7 sigma from zero, so it is not scatter around zero; a value
repeated 23 times to six decimal places is a pipeline sentinel or floor, not
23 independent measurements. Two further rows sit nearby at `-0.264236` and
`-0.265486`.

**These rows are retained unfiltered.** The task definition is the released
data, and dropping rows would make this package a different task from the one
the benchmark publishes. They are 0.62% of the population. A model is not
expected to reproduce the sentinel, and the forward contract deliberately
forbids a squashing output activation so the negative range stays reachable.

**3. The long tail exists only in train.** Train reaches `frot = 17.45`;
validation stops at 2.85 and test at 3.01. Training and validation therefore
have materially different target variance, which is a second reason an
R-squared computed on one population cannot be compared to one computed on
another.

## Preprocessing authority

`runtime/tess_data_path.py::normalize_curve` is the single authority:
right-truncate to 1024 or pad with the last observed flux value, and z-score
**before** padding. The staging tool stores raw flux precisely so that it
cannot become a second preprocessing authority.

The paper states only that "models are applied to the normalized time
series" without specifying the method. Per-curve z-scoring is the operator's
frozen choice for this package (2026-09-20), consistent with the explicit
rule PhyTS documents for its Project 8 subset.

## Reference figures and architectures

PhyTS Table 2, TESS regression (R-squared): mean baseline `-0.017`, CNN
`0.617`, LinOSS `0.612`, S4D `0.665`. Table 10 reports a per-size sweep.
**Nothing in this repository has reproduced any of these numbers.**

They are treated as **common knowledge rather than as a prior**: anyone who
reads the benchmark has them, so they belong to the task and both information
treatments see them. The full record is `declared/reference_baselines.json`,
and a summary reaches the agents through `declared/task_config.yaml`, which is
the field the framework routes into node prompts. An executable guard keeps
these figures out of the experiments' advice artifact, because restating them
there would make the no-prior arm ignorant of the published context rather
than merely unadvised.

Baseline architectures come from the benchmark's **code repository**
(`github.com/kyoon-mit/PhyTS`, `src/models/` and `configs/TESS/`, read
2026-09-20). The paper publishes only family names and calls its
convolutional baseline "a vanilla CNN".

### Three discrepancies between that repository and the paper

Recorded rather than resolved; each is checkable against the cited files.

**Parameter count.** Table 8 reports 300K for all three supervised baselines
on this dataset. The committed CNN config measures **926,536** parameters —
constructed from the config and counted, not quoted — and the LinOSS config's
own comment targets S4D at approximately 662K. The committed configs
therefore sit near the sweep's ~700k point, not the ~300k point the headline
results come from. That matters because Table 10 shows S4D **falling from
0.665 at ~300k to 0.522 at ~700k**: the committed config is not the
configuration that produced the best published number.

**Split.** The committed conv and S4D configs use `train_frac 0.7` /
`val_frac 0.15` — appendix D.2's 70/15/15 re-split, not the released 80/10/10
grouped by Gaia DR3 identifier that this package uses.

**Task coverage.** The repository commits **no regression config for TESS at
all**, only classification. The backbones and code paths are the same three
families; only the output width and loss differ. So the recorded structures
describe the rotation-regression baselines' shape, but not a configuration
that was literally run for Task B.
