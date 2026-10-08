# Install the tutorial environments and configure keys

This setup sequence serves **TESS, TIDMAD, Project8 and LIGO**. Choose one of
those [paper-task guides](../../paper/README.md), install its two environments
here, then return to create the external project, data and notebook kernel.

For Pet, MJD, SuperNEMO, Cancer or DAVIS, use the complete installation steps
in its [supplementary task guide](../../supplementary/README.md) instead. Those
guides own their environment-variable names; do not combine installation blocks.

## Before installing

Use Linux, Python 3.12, `git` and `uv`. The frozen environment uses CUDA packages.
Training needs a supported NVIDIA GPU with working memory accounting; device
names are not restricted to the authors' hardware. CPU machines can inspect
files and plots but cannot run these training demos. AMD/ROCm is experimental
and lacks required accounting; Intel GPU training is unsupported. Read the
[hardware guide](../hardware/README.md) before a large data download.

The [tutorial directory guide](../../README.md#source-project-data-and-run-directories)
explains source checkouts, your external project, input data and per-run outputs.
Keep credentials separate from those locations.

## 1. Install the two exact checkouts

Choose new paths, then run these commands in one terminal:

```bash
export EXP_CHECKOUT="/absolute/path/to/siderius-exp"
git clone https://github.com/yuema137/siderius-exp.git "$EXP_CHECKOUT"
cd "$EXP_CHECKOUT"
uv sync --python 3.12 --group dev --group tutorial --frozen

export INFRA_CHECKOUT="/absolute/path/to/SIDERIUS-tutorial"
git clone https://github.com/yuema137/SIDERIUS.git "$INFRA_CHECKOUT"
git -C "$INFRA_CHECKOUT" checkout --detach "$(cat "$EXP_CHECKOUT/SIDERIUS_REVISION")"
(cd "$INFRA_CHECKOUT" && uv sync --python 3.12 --group dev --frozen)
```

Exp's environment runs notebooks and preparation tools. Infra's environment
executes the research workflow. Keep both checkouts clean: edit the copied files
in your external project. Do not share virtualenvs, inject another checkout's
source through `PYTHONPATH`, or change the version pin to bypass an error.

New projects copy the independent [Luna test profile](../README.md). The native
planner is built into infra; these demos do not need a historical planner plugin.
Preview compares the selected planner across both environments. A mismatch means
restore the paired installations before launching, not disable the check.

For an existing project, keep its selected source pair. To adopt a newer pair,
create a fresh project and run workspace, then transfer intended parameter edits.
Do not resume an old workspace under a new source pin.

## 2. Export keys before starting Jupyter

New tutorial routing uses OpenAI and requires `OPENAI_API_KEY`. Changing enabled
routes/providers may require other keys; the saved script's preview reports
names and presence. The task guide says which optional workflow stages are active.

In the terminal that will launch Jupyter or the saved script:

```bash
read -r -s -p "OpenAI API key: " OPENAI_API_KEY
echo
export OPENAI_API_KEY
```

The value is not echoed or stored in shell history. For repeated use, load a
trusted external mode-600 environment file into that same shell. Do not put keys
in notebook cells, command arguments, experiment JSON, `llm/agents.json` or Git.
A credential file's existence does not export its contents.

**Start Jupyter from this configured terminal.** If the server is already
running, stop it and restart it here; restarting only its kernel does not update
the server's inherited environment. A separate terminal needs its own exports.

Checks show required variable names, not key values, and launch refuses missing
or whitespace-only keys. Presence is not proof of provider access or credit.
Model selection and training budgets do not cap the total number/cost of API
calls; inspect the [LLM configuration levels](../README.md) before scaling up.

## 3. Return to the task's project and data steps

Keep `EXP_CHECKOUT` and `INFRA_CHECKOUT` exported. Each guide supplies its exact
initializer, data route, project path and kernel commands:

- [TESS](../../paper/tess/README.md)
- [TIDMAD](../../paper/tidmad/README.md)
- [Project8 or LIGO](../../paper/prepared/README.md)

Follow the selected guide to initialize a fresh external project and download
and prepare its dataset. Initialization alone does not supply data. If you have
already completed that preparation on your machine, keep it for later runs.

Before paid execution, inspect the saved JSON/script, run the task's preview,
and check the exact JSON with the [hardware-only command](../hardware/README.md).
That check needs no API key but queries the GPU and executes a tiny kernel.
It is a current snapshot, not a memory reservation or proof a generated model fits.

The task guide tells you which notebook to open and which saved script it will
run. Use one launch route: notebook Run All can already invoke that script.
After completion, plot existing records instead of launching again. A low or
invalid score is still useful process evidence; do not weaken checks to force a pass.
