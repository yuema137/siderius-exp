# PhyTS LIGO chirp-mass regression

Estimate chirp mass in solar masses from two whitened detector channels.
The task uses the owner-supplied PhyTS paper's fixed 59–63 second window:
`whitened_injected[:, 15104:16128]`, float32 `[2, 1024]`, without per-example
amplitude normalization. Target: stored `chirp_mass`, in physical solar masses.

## Start with the tutorial

The [LIGO/Project8 setup guide](../../tutorials/paper/prepared/README.md) explains
installation, external data and project creation. Open the
[LIGO notebook](../../tutorials/paper/notebooks/04_ligo_tutorial.ipynb) to see the
detector input and recorded results, then run a small three-iteration demo.
The demo uses reduced data; the full research scopes below remain separate.
It is not a complete paper reproduction.

## Scientific task and research scopes

Start with [the composition](compositions/regression.yaml) and
[the scientific/forward contract](declared/task_config.yaml).
[The prepared declaration](declared/prepared.json) pins a separately stored
manifest and the fixed loss-subset row indices. No targets are committed.

The released 360,000 training / 90,000 validation rows are preserved. Training
selection remains free within the experiment's budgets. Formal evaluates all
90,000 validation rows; epoch loss uses the frozen 9,000-row subset, with 1,000
rows per released SNR bin. Released split names are preserved despite the
paper's inconsistent O3a/O3b wording. Test is absent from the campaign view.

Prepared arrays follow the [shared adapter contract](../shared/prepared_regression.md).
Global R2 is the primary selection metric; global RMSE is secondary. Both
are computed in physical units. Validation scores are not paper test scores.

No advice, baseline recipes, or student scaling results are supplied by this
task to a NoPrior agent. [The experiment](../../experiments/phyts_ligo/main_fixed_workflow/README.md)
owns the budgets and information treatment.
