# PhyTS TESS experiments

Bounded treatments of [`tasks/phyts_tess`](../../tasks/phyts_tess/) — near-core
rotation regression from TESS light curves, selected on R-squared.

| experiment | what it is | state |
|---|---|---|
| [`main_fixed_workflow/`](main_fixed_workflow/README.md) | SIDERIUS reference workflow, 1 trial + 1 formal per iteration, 6-hour budget, one RTX 5090 | no-prior arm only; never run |
| `main_orchestrator/` | agent-selected capabilities | **not written yet** |
| `coding_agent_baseline/` | general coding agent on the same task | **not written yet** |

The information treatment — what the agent is told — is a separate axis from
the workflow, and lives in
[`information_treatments/`](information_treatments/README.md). Only the
no-prior treatment exists today.

An experiment selects one static task package and one workflow, then owns the
concrete treatment: parameter values, advice, budgets and result identity.
Changing any treatment value creates a **new experiment identity**; it does
not modify the task package.

The presence of a launcher is not authorization to run it.
