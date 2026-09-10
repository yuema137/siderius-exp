# Recovered Majorana model-demo record

## Status

The local workspace `majorana_model_demo_v3_lit_on` survives and is the source
for this recovery record. It contains completed manifests for iterations 1--11
and 21--29. Iterations 12--20 contain `no_records` manifests after the original
time windows repeatedly refused candidates. Iteration 30 is incomplete and is
not reported as evidence.

SIDERIUS execution used commit `6bcdeb2f55b47ced6bcadaa08ddfd88875964261`,
which is stamped in the per-iteration hardware records. The experiment
checkout was created for siderius-exp commit
`cb020b439282710a8381ca875c15d0893db21df3`; this value is recovered from the
checkout identity and launch record rather than from a dedicated workspace
revision stamp.

The reusable scientific definition remains in
[`../../tasks/majorana_low_avse/`](../../tasks/majorana_low_avse/): the task
description and model-I/O contract, official Train/Test-aware data adapter,
fixed-bin energy-matched ROC-AUC implementation, secondary ordinary ROC AUC,
input-leakage exclusions, reference model, agent-facing scientific blocks,
dataset manifest, and literature-review root-paper declarations. This recovery
record adds no second copy of those authorities.

## Recovered continuation treatment

Iterations 21--30 were launched against the existing workspace so that the
first 20 iterations could continue to supply history and incumbents. The
effective command was:

```bash
bash experiments/majorana_low_avse/launch.sh \
  --profile demo \
  --literature on \
  --siderius-checkout /absolute/path/to/SIDERIUS \
  --workspace /absolute/path/to/majorana_model_demo_v3_lit_on \
  --data_dir /absolute/path/to/MAJORANA \
  --start_iter 21 \
  --num_iterations 30 \
  --trial_time_budget_minutes 20 \
  --formal_time_budget_minutes 40
```

The inherited `demo` treatment supplied two rounds, deterministic snapshot
selection, a 10-GiB Trial and Formal VRAM ceiling, `trial_portion=0.50`,
`train_portion=0.05`, `eval_portion=0.05`, `formal_portion=1.0`,
`formal_train_portion=0.10`, `formal_eval_portion=0.10`, Literature Review ON,
and an epoch rule of `[5, 50]`.

## Recovered scientific evidence

The compact machine-readable trajectory is stored in
[`receipts/recovered_model_demo_v3_trajectory.json`](receipts/recovered_model_demo_v3_trajectory.json).
The best recovered Formal result is iteration 29 at
`energy_matched_roc_auc=0.9855665373752355`. The missing points at iterations
12--20 are intentional: those iterations produced no valid scored candidate.
Iteration 30 is excluded because it has no completed manifest.

Raw HDF5 data, generated models, checkpoints, and the workspace remain outside
Git.
