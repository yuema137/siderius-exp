# PhyTS Project 8 electron-energy regression

## Start with the tutorial

The [Project8/LIGO setup guide](../../tutorials/paper/prepared/README.md) and
[Project8 notebook](../../tutorials/paper/notebooks/03_project8_tutorial.ipynb)
show how to inspect data, save parameters, run a three-iteration demo and plot
results in your own external project. This is a simplified process demo, not a
complete paper reproduction.

The teaching demo uses **time and frequency views together**, the separately
versioned [dual-representation task](DUAL_REPRESENTATION.md). Its four input
channels are distinct from the original two-channel task below. Keep their
configurations and recorded results separate.

## Original time-only task


Estimate electron energy in eV from two noisy CRES I/Q time series.
Inputs are `I + I_cav_noise` and `Q + Q_cav_noise`, retaining all 24,576
samples per channel. Each event/channel is centered and divided by its own
population standard deviation before float32 storage. Constant channels
become zero. No FFT or crop is applied. Target: physical `energy_eV`.

Start with [the composition](compositions/regression.yaml) and
[the scientific/forward contract](declared/task_config.yaml).
[The prepared declaration](declared/prepared.json) pins a separately stored
manifest and the fixed loss-subset row indices. No targets are committed.

The released 40,000 training / 5,000 validation rows are preserved. Training
selection remains free within the experiment's budgets. Formal evaluates all
5,000 validation rows; epoch loss uses the frozen 500-row subset. The released
5,600 test rows are absent from the campaign view. The released counts agree
with appendix D rather than the inconsistent main-text total of 50,827.

The owner-supplied paper is the preprocessing authority. The public repository's
older FFT/crop configuration is not used. Prepared arrays follow the
[shared adapter contract](../shared/prepared_regression.md). Global R2 is the
primary selection metric; global RMSE is secondary. Both use physical eV values.

No advice or baseline recipe is supplied by this task to a NoPrior agent.
[The experiment](../../experiments/phyts_project8/main_fixed_workflow/README.md)
owns budgets and information treatment. Identical preprocessing does not make
validation scores directly comparable to published test scores.

## Dual-representation task

The separately versioned [time/frequency task](DUAL_REPRESENTATION.md) requires both supplied representations and includes cited physical context. It does not overwrite this original time-input contract.
