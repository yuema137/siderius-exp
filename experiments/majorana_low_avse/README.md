# Majorana Low-AvsE experiments

**For a first run, use the [three-iteration Majorana Low-AvsE tutorial](../../tutorials/supplementary/mjd/README.md).**
It explains data setup, editable settings, the saved launch script and results.
Its [teaching template](tutorial_demo/README.md) is separate from the research
profiles below; the profile named `demo` runs **30 iterations**.

## Research profiles

`launch.sh` exposes three profiles:

- `qualification`: two iterations, one Trial round plus one forced Formal
  round, one epoch, a one-minute Trial budget, a two-minute Formal budget, and
  small data scopes;
- `campaign`: 20 iterations, three rounds, agent-selected 5–50 epochs,
  10-minute Trial and 30-minute Formal budgets, and 10-GiB VRAM ceilings;
- `demo`: the separate 30-iteration treatment described below; it is not a
  three-iteration tutorial.

The independent `--literature on|off` switch is the only intended variable
between the primary campaign and its fresh control.

The campaign uses 20% × 20% of official Train for Trial, and 100% × 20% for
Formal. Trial evaluates on 20% of official Test; Formal evaluates on all of it.
Every scope is balanced exactly by class inside fixed 25-keV energy bins.

Always use a fresh workspace and campaign identity for the Lit OFF control.

The separate `demo` profile runs 30 iterations with one Trial round followed
by one forced Formal round. Trial uses half of the Formal scope, with a
10-minute Trial budget and a 20-minute Formal budget; Formal uses 10% of
official Train and 10% of official Test. The launcher locks both training and
evaluation selection to deterministic snapshot scopes. The versioned demo
advice states the same time and 10-GiB VRAM limits to the proposer and tuner;
its SHA-256 is pinned by the launcher.

The actual September 2026 demo later continued at iteration 21 with 20-minute
Trial and 40-minute Formal budgets after the original windows caused repeated
measured-time refusals. Its mixed-treatment history and recovered trajectory
are recorded in
[`recovered_model_demo_v3_2026-09-09.md`](recovered_model_demo_v3_2026-09-09.md).
The reusable `demo` defaults remain unchanged; reproducing the historical
continuation requires the explicit overrides in that record.
