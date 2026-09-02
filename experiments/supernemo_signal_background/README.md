# SuperNEMO experiments

The static scientific task lives under
`tasks/supernemo_signal_background/`. This directory owns workflow treatment.

- `qualification`: two iterations, one Trial round plus one forced Formal
  round, one epoch, 1% scope with a 1% per-epoch training subsample, 1%
  evaluation, one-minute Trial/Formal budgets, and a 10-GiB VRAM ceiling. It
  proves the external task path, not scientific performance.
- `campaign`: 20 iterations and three rounds under the operator-approved
  treatment. Agents choose 5--50 epochs and architecture-specific batch sizes.
  Trial uses 20% scope and 20% of that scope for training; Formal uses the full
  declared scope and 20% for training. Evaluation portions are 20% and 100%,
  respectively. Trial has 10 minutes, Formal has 30 minutes, and both have a
  10-GiB VRAM ceiling.

Both profiles use normal measured admission and normal Trial-to-Formal
promotion. Neither bypasses resource budgets or Formal execution.

```bash
bash experiments/supernemo_signal_background/launch.sh \
  --profile qualification \
  --siderius-checkout /absolute/path/to/pinned/SIDERIUS \
  --workspace /absolute/path/to/fresh/workspace \
  --data_dir /absolute/path/to/supernemo/data
```

Replace `qualification` with `campaign` only after qualification passes at the
same exact repository pair. Raw HDF5 files and generated `event_indexes` remain
outside this repository.
