# Majorana Low-AvsE experiments

`launch.sh` exposes three profiles and an orthogonal literature switch:

- `qualification`: two iterations, one Trial round plus one forced Formal
  round, one epoch, a one-minute Trial budget, a two-minute Formal budget, and
  small data scopes;
- `campaign`: 20 iterations, three rounds, agent-selected 5–50 epochs,
  10-minute Trial and 30-minute Formal budgets, and 10-GiB VRAM ceilings;
- `--literature on|off`: the only intended variable between the primary
  campaign and its fresh control.

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
