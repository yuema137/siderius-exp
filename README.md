# siderius-exp

Scientific tasks and their experiments for the SIDERIUS framework.
This repository is the place where task meaning and experiment choices live;
the generic framework lives in the separate [SIDERIUS repository](https://github.com/yuema137/SIDERIUS).

## Paper

[Beyond a Better Score: Long-Horizon Agentic ML Development and Evaluation Protocol for Physics Time Series](https://zenodo.org/records/23071121)
introduces SIDERIUS and evaluates agent-driven model development on TIDMAD,
TESS, Project8, and LIGO. It combines reusable research capabilities, scientific
validity checks, and exploration within compute budgets, evaluating whether
models are scientifically valid as well as how well they score.

This repository provides the task packages, experiment configurations, and
archived evidence. The tutorials below are simplified workflow demos; use the
[paper artifact reference](experiments/paper-artifacts.md) for reproduction
configurations and the available historical records.

For a first flow check, use the inexpensive Luna test configuration. For
production research, we recommend starting with the paper's LLM configuration;
your own supported model choices are also welcome. See
[LLM configuration levels](tutorials/shared/README.md) for the files to edit
and the distinction between model selection and historical replay.

## Start here

For a guided notebook plus terminal-script example, start with the
[tutorial index](tutorials/README.md), then choose TESS, one-band TIDMAD,
Project8 (time/frequency inputs), or LIGO. The [paper tutorial guide](tutorials/paper/README.md) explains setup and
supported changes. These are simplified demos, not one-click paper artifact
reproduction. For frozen source/configuration pairs and archived evidence, use
the [paper artifact reference](experiments/paper-artifacts.md).

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
campaign. A task declares scientific meaning independently of the workflow.
Intentional scientific changes create a new task identity. Changing a workflow
treatment creates a different experiment, not a different task.

<a id="framework-revision"></a>

## Environments and data

The dependency is pinned by [`SIDERIUS_REVISION`](SIDERIUS_REVISION),
`pyproject.toml`, and `uv.lock`. Use the exact checkout's own environment:

```bash
uv sync --group dev --frozen
```

Do not mix checkouts with `PYTHONPATH`, another virtualenv, or an editable
install. For API-backed work, inject the enabled providers' keys into the
launching process from a mode-600 external file or managed secret. Never
commit credentials. The fixed-workflow supervisor checks its environment
before starting; a file that a later child might load cannot satisfy that
check. Raw datasets, generated output, caches and workspaces stay external.
The complete agent contract is in
[`CLAUDE.md`](CLAUDE.md#environment-and-launch-credentials).

<a id="running-the-live-tests"></a>

## Validation

Tests that inspect or execute framework source require an explicit
`SIDERIUS_CHECKOUT`; those checks fail when it is missing. Follow the selected
experiment's validation instructions. To collect tests without running them:

```bash
SIDERIUS_CHECKOUT=/path/to/pinned/SIDERIUS .venv/bin/python -m pytest --collect-only -q
```

Current task and campaign status is recorded by their `STATUS.md` or current
index. Historical records are evidence, not launch authorization.

## Task, experiment, and campaign are different things

Use a **task package** when you need to change scientific meaning: data layout,
model input/output, objective, metric, deliverable encoding, or Health rules.
Use an **experiment** when you need to change how the search runs: information
treatment, advice, model routing, band, iteration/round schedule, time/VRAM
budget, or workspace identity. Use a **campaign** when you coordinate several
experiment units.

For TIDMAD, a different existing band can use the fixed-workflow launcher with
a different `--band` and external `--data_dir`. A new scientific parent or file
identity requires a new task/experiment binding and provenance; it should not
be hidden in a shell argument or an old run receipt.

## More detail

- [task index](tasks/README.md)
- [experiment index](experiments/README.md)
- [campaign index](campaigns/README.md)
- [migration evidence](provenance/MIGRATION.md)
- [framework task-composition contract](https://github.com/yuema137/SIDERIUS/blob/b13b9263c939c33b8d06361b1ae2fd0f99c3a900/docs/reference/task-composition.md)

## License

Original siderius-exp software and documentation are available under the
[MIT License](LICENSE). Third-party code, datasets and data-derived examples
retain their own terms and attribution; see [NOTICE](NOTICE) and the selected
task's provenance. The project license does not grant new rights to external
data, paper content or dependencies.
