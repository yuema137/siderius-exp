# PhyTS TESS — near-core rotation regression

Predict a pulsating star's **near-core rotation frequency** from a single
TESS light curve. One star observed in one sector is one sample; the model
sees 1024 normalized brightness samples and returns one number in cycles per
day.

This is PhyTS Task B for TESS. The benchmark's eight-class variability
classification (Task A) is **not** part of this package.

| | |
|---|---|
| primary metric | **R-squared, higher is better** |
| secondary | RMSE, MAE — observational, never ordering |
| input | `[B, 1, 1024]` float32 |
| output | `[B, 1]` float32, unbounded |
| population | 3,338 train / 442 validation curves; 403 held out |

## Start with the tutorial

Follow the [TESS setup and notebook guide](../../tutorials/paper/tess/README.md)
to create your own external project, inspect example light curves, change search
settings and run a three-iteration demo. It shows saved files and results; it is
not a complete paper reproduction.

For research settings, see the [fixed-workflow experiment](../../experiments/phyts_tess/main_fixed_workflow/README.md).
For recorded paper runs, use the [artifact reference](../../experiments/paper-artifacts.md).

## Inspect or integrate this task package

1. Stage a run data root — [`data/README.md`](data/README.md) has the one
   command. The held-out test split is deliberately not staged.
2. Select [`compositions/rotation_regression.yaml`](compositions/rotation_regression.yaml)
   from an experiment. The composition declares the science; it contains no
   iteration counts, budgets or launch policy.
3. Run the pack's contract checks:

   ```bash
   PHYTS_TESS_DATA_DIR=/path/to/run-data \
       .venv/bin/python -m pytest tests/tasks/phyts_tess -q
   ```

   Without `PHYTS_TESS_DATA_DIR` the data-backed cases skip, and a skip means
   unverified rather than passed.

Read [`STATUS.md`](STATUS.md) before treating any of this as qualified, and
[`PROVENANCE.md`](PROVENANCE.md) before interpreting a score.

## What this package owns

| file | responsibility |
|---|---|
| [`runtime/tess_data_path.py`](runtime/tess_data_path.py) | scope construction and transport, dataset materialization, the frozen preprocessing, deliverable codec |
| [`runtime/scoring.py`](runtime/scoring.py) | R-squared, RMSE and MAE |
| [`runtime/scoreability.py`](runtime/scoreability.py) | whether a deliverable is scoreable at all |
| [`declared/`](declared/) | dataset profile, task description and forward contract, metric declarations, Health family |
| [`declared/reference_baselines.json`](declared/reference_baselines.json) | the benchmark's published results, baseline architectures, and three recorded paper/repository discrepancies |
| [`plugins/`](plugins/) | reference model, Health view provider |
| [`data/manifests/`](data/manifests/) | the committed split authority |
| [`tools/stage_data.py`](tools/stage_data.py) | staging, and the test-split isolation |

## Three things worth knowing before reading a score

**R-squared is normalized by the evaluation set's own variance.** Two values
are comparable only over the same evaluation population. A number from a
`portion < 1.0` round is not comparable to a full-validation number, and
neither is comparable to the PhyTS test-set figure. RMSE carries the physical
unit and is the right number to quote across differently scoped rounds — it
just never orders candidates.

**The labels have a noise floor.** `frot` is derived per light curve, not per
star, so the same star can carry different targets in different sectors. A
model that predicted each star's mean target perfectly would score R-squared
0.92 on train and 0.98 on validation. The PhyTS baselines reach 0.665, so the
floor is not what limits current models — but it is what the metric
eventually saturates against.

**No training objective is declared.** The agent chooses its own loss. The
selection metric is unaffected: training objective and selection metric are
separate declarations, and only the latter orders candidates.

## Published baselines are common knowledge, not a prior

The benchmark's own numbers and baseline architectures live in
[`declared/reference_baselines.json`](declared/reference_baselines.json), and
a summary reaches the agents through the task description. Anyone reading the
benchmark has them, so **both** information treatments do — a no-prior arm
that did not know the published context would be ignorant rather than merely
unadvised, which is a different contrast. What to *do* about them is advice,
and belongs to an experiment.

They do not line up cleanly with the repository, and the discrepancies are
recorded rather than smoothed: the committed configs measure near ~700k
parameters against a reported 300K, use a 70/15/15 split rather than the
released 80/10/10, and cover only the classification task. See
[`PROVENANCE.md`](PROVENANCE.md).

## Not declared, deliberately

- **No `objective:`** — see above.
- **No `deliverable:`** — the task names its own artifacts through a
  module-level `deliverable_name`, so a composed run is refused an indexed
  template rather than silently handed another task's.
- **`interpretation_blocks: {none: true}`** — a named absence. Saying nothing
  would resolve TIDMAD's interpretation family, whose axion-denoising science
  has nothing to say about stellar rotation.
