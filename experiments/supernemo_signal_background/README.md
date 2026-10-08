# SuperNEMO experiments

**For a first run, use the [three-iteration SuperNEMO tutorial](../../tutorials/supplementary/supernemo/README.md).**
It explains data setup, editable settings, the saved launch script and results.
Its [teaching template](tutorial_demo/README.md) is separate from the research
profiles below; the profile named `demo` runs **30 iterations**.

## Research profiles

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

The `demo` profile is a separate bounded treatment: 30 iterations, one Trial
round followed by one forced Formal round, a five-minute Trial budget, and a
ten-minute Formal budget. Trial uses half of the Formal scope. It does not
replace the `campaign` profile.
The workflow locks both training and evaluation selection to deterministic
snapshot scopes because this task's external data adapter exposes that one
selection policy. The lock uses SIDERIUS's generic ``plan_overrides`` contract;
the adapter still refuses unsupported strategies as defense in depth.

The September 2026 model-demo continuation used larger measured time budgets
and smaller data scopes than the original `demo` defaults. RunPod was deleted
before its workspace could be retained. The recoverable launch treatment,
metric trajectory, and provenance limitations are recorded in
[`recovered_model_demo_v3_2026-09-03.md`](recovered_model_demo_v3_2026-09-03.md).
That record does not change the reusable `demo` profile and must not be read as
a completed campaign.

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
