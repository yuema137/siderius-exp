# Recovered SuperNEMO model-demo record

## Status

This is a recovery record for the deleted RunPod workspace
`supernemo_model_demo_v3_lit_on`. It is not a completed campaign and does not
authorize resumption from the deleted workspace.

The last locally retained dashboard receipt proves scored results through
iteration 10 and a Trial result for iteration 11. The RunPod checkout and full
workspace were deleted before they could be archived. Consequently, the exact
siderius-exp commit used by the live process cannot be established from a
workspace provenance stamp. The checkout pathname contained `2dad4c0`, but a
pathname is not accepted as repository identity. The launch surface used the
`demo` profile added no later than `c2db9a7`.

SIDERIUS execution used commit `7568fc54b6bcc00ce6ee5c1e88f3219550a688cb`.

The reusable scientific definition remains in
[`../../tasks/supernemo_signal_background/`](../../tasks/supernemo_signal_background/):
the task description and model-I/O contract, event-level data adapter,
fixed-bin energy-matched ROC-AUC implementation, secondary ordinary ROC AUC,
feature-leakage exclusions, model plugin, agent-facing scientific blocks, and
literature-review root-paper declaration. This recovery record adds no second
copy of those authorities.

## Recovered continuation treatment

The original model-demo identity was retained so iterations 1--8 could feed
iteration 9. The incomplete first attempt at iteration 9 was quarantined before
the continuation. The effective continuation arguments were:

```bash
bash experiments/supernemo_signal_background/launch.sh \
  --profile demo \
  --siderius-checkout /absolute/path/to/SIDERIUS \
  --workspace /absolute/path/to/supernemo_model_demo_v3_lit_on \
  --data_dir /absolute/path/to/SUPERNEMO_DATA \
  --start_iter 9 \
  --num_iterations 30 \
  --run_name supernemo_model_demo_v3_lit_on \
  --train_portion 0.027 \
  --formal_train_portion 0.054 \
  --trial_time_budget_minutes 15 \
  --formal_time_budget_minutes 30
```

The inherited `demo` treatment supplied two rounds, a 10-GiB Trial and Formal
VRAM ceiling, deterministic snapshot selection, `trial_portion=0.50`,
`eval_portion=0.50`, `formal_portion=1.0`, `formal_eval_portion=1.0`, Literature
Review ON, and an epoch rule of `[5, 50]`.

The live `run_one_iteration.py` process was independently observed with
`start_iteration=9`, Trial/Formal budgets of 15/30 minutes, and training
portions of 0.027/0.054. Resume output restored eight prior plugins, 41
accumulated findings, the iteration-2 incumbent, the iteration-8 Trial
incumbent, and eight prior tuning outputs before iteration 9 began.

## Recovered scientific evidence

The compact machine-readable trajectory is stored in
[`receipts/recovered_model_demo_v3_trajectory.json`](receipts/recovered_model_demo_v3_trajectory.json).
Its last authoritative Formal result is iteration 10 at
`energy_matched_roc_auc=0.7430732765673952`. Iteration 11 has only a recovered
Trial result and is provisional. No claim is made for iterations 12--30.

Raw data, generated models, and runtime output are intentionally absent from
this repository.
