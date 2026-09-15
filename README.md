# siderius-exp

Private scientific tasks and their experiments for the SIDERIUS framework.
This repository is the place where task meaning and experiment choices live;
the generic framework lives in the separate [SIDERIUS repository](https://github.com/Galileo-Sandbox/SIDERIUS).

## Start here

1. Choose a scientific problem in [`tasks/`](tasks/README.md).
2. Choose one bounded treatment in [`experiments/`](experiments/README.md).
3. Use [`campaigns/`](campaigns/README.md) only for coordinated, multi-run work.
4. Put data, workspaces, logs, models, and secrets outside both repositories.

The shortest safe path is to read the relevant task page, then the experiment
page, and use its dry-run command before an effectful launch.

## What belongs here

- `tasks/`: scientific meaning, data identity, splits, plugins, metrics, and validity rules.
- `experiments/`: one task plus one workflow and its concrete parameters, advice, budgets, and result identity.
- `campaigns/`: authorization and coordination across runs, bands, or stages.
- `deployments/`: machine and scheduler setup.
- `provenance/`: dated migration and validation evidence.

Task, experiment, and campaign are separate axes. Trial and Formal are
workflow roles; they may appear in an ordinary experiment as well as in a
campaign. A task is static. Changing a workflow treatment creates a different
experiment, not a different task.

## Environments and data

The dependency is pinned by [`SIDERIUS_REVISION`](SIDERIUS_REVISION),
`pyproject.toml`, and `uv.lock`. Use the exact checkout's own environment:

```bash
uv sync --group dev --frozen
```

Do not mix checkouts with `PYTHONPATH`, another virtualenv, or an editable
install. For API-backed work, prepare the required `.env` in the selected
SIDERIUS checkout before launch; never commit credentials. Raw datasets,
generated output, caches, and workspaces remain machine-local.

## Validation

The live test suite requires an explicit `SIDERIUS_CHECKOUT`; it intentionally
fails when that boundary is missing. Follow the exact command in the relevant
experiment or campaign README. For a quick, no-data check:

```bash
.venv/bin/python -m pytest --collect-only -q
```

Current task and campaign status is recorded by their `STATUS.md` or current
index. Historical records are evidence, not launch authorization.

## More detail

- [task index](tasks/README.md)
- [experiment index](experiments/README.md)
- [campaign index](campaigns/README.md)
- [migration evidence](provenance/MIGRATION.md)
- [framework task-composition contract](https://github.com/Galileo-Sandbox/SIDERIUS/blob/e712d8544b7b10b57618a0ba309d39d1098815f7/docs/reference/task-composition.md)
