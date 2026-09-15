# TIDMAD time-series denoising

TIDMAD is a scientific task for cleaning long SQUID detector time series. One
sample is a long signal segment; the model predicts a cleaned signal at each
time step. This package owns the task definition and its reference material.
It does not contain the generic SIDERIUS framework.

## Start here

- Current capability and limitations: [`STATUS.md`](STATUS.md)
- Data identity and historical evidence: [`PROVENANCE.md`](PROVENANCE.md)
- How to prepare the external data root: [`data/README.md`](data/README.md)
- A bounded reproducible run: [qualification experiment](../../experiments/tidmad/two_iteration_qualification/README.md)

## What the package provides

The task directory contains the composition, resolved declarations, task
plugins, scoring references, and data-root adapter. It never contains raw HDF5
data. The reference files under `reference_data/` are task-owned rulers and
historical comparison material; they are not a substitute for the external
dataset.

The task's scientific metric is `tidmad_denoising_score` and higher is better.
The task composition and resolved files are the authority for model I/O,
dataset identity, deliverables, and metric details. Edit those owners only;
do not create a second copy in a launcher or framework checkout.

For continuous-regression runs, the task-owned `model_io.inference`
declaration standardizes the same per-ML-segment forward values used by
ordinary composed evaluation before deliverable storage encoding. The
candidate configuration remains the sole owner of `segmentation_size`; the
task adapter consumes the resolved value and never supplies a hidden default.
Historical inference inputs use the exact serialized task scope and expose
only the requested input channel. Targets are materialized through a separate
authorization path.

## Quickstart

Use a fresh workspace and an explicitly staged data directory. Preview first:

```bash
bash experiments/tidmad/two_iteration_qualification/launch.sh \
  --siderius-checkout /absolute/path/to/SIDERIUS \
  --workspace /absolute/path/to/fresh/workspace \
  --data_dir /absolute/path/to/tidmad/data \
  --dry-run
```

Run the same command without `--dry-run` only after checking the printed
revision, inputs, and workspace. The launcher owns workflow treatment; this
task package does not decide iteration counts, budgets, or campaign
authorization. Outputs go under the external workspace, never this checkout.

Before composed scoring, follow the anchor staging instructions in
[`data/README.md`](data/README.md). The staged anchor must be compared with
the committed ruler; merely having a file with the right name is insufficient.

## Boundaries

The old `examples/tidmad` projection is historical and is not an authoring or
launch surface. Older framework revisions and result records in `STATUS.md`
and `PROVENANCE.md` remain dated evidence. A new experiment must select this
task explicitly and use its own workspace; no task default is inferred from a
directory name.
