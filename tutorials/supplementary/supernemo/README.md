# SuperNEMO event-classification tutorial

Learn how one detector event becomes a model input, edit your own saved
experiment, run three research iterations, and plot their measured scores.
The [notebook](supernemo_tutorial.ipynb) explains and edits files; a saved shell
script starts the experiment. This is a supplementary process demo, not a
paper reproduction or a promise of a particular score.

**Live three-iteration qualification is still pending.** Data inspection and
offline checks are separate from successful training. No current score gallery
is claimed until that qualification is complete.

An event contains multiple detector-hit rows. Its identity is
`(process, ev_no)`; those rows stay together when assigning data partitions.
The model receives up to 224 hits, padded to an input of shape `[224,11]`, and
predicts signal (`0nubb`) versus background (`2nubb`, `Bi214`, `Tl208`).
Truth angles and the event ID are not model features.

## 1. Install the paired environments

Choose absolute paths for the two source checkouts and three external folders.
Replace the examples below before running commands:

```bash
export EXP_CHECKOUT="/absolute/path/siderius-exp"
export INFRA_CHECKOUT="/absolute/path/SIDERIUS"
export RAW_DATA="/absolute/path/data/supernemo-raw"
export PREPARED_DATA="/absolute/path/data/supernemo-prepared"
export TUTORIAL_HOME="/absolute/path/my-supernemo-project"

git clone https://github.com/yuema137/siderius-exp.git "$EXP_CHECKOUT"
git clone https://github.com/yuema137/SIDERIUS.git "$INFRA_CHECKOUT"
cd "$EXP_CHECKOUT"
uv sync --python 3.12 --group dev --group tutorial --frozen
git -C "$INFRA_CHECKOUT" checkout "$(cat SIDERIUS_REVISION)"
cd "$INFRA_CHECKOUT"
uv sync --python 3.12 --group dev --frozen
```

If you already have the checkouts, use their paths instead of cloning again.
Each checkout needs its own frozen `.venv`. Live training needs the supported
GPU environment described by the [shared checks](../../shared/gpu-runtime.md).
The initial VRAM allowance is 10 GiB; it must fit the selected device. On a
multi-GPU machine, set `CUDA_VISIBLE_DEVICES` before starting Jupyter or the
script. Offline inspection needs neither GPU training nor API credentials.

## 2. Reuse raw data and prepare event indexes once

If the four official files already exist locally, set `RAW_DATA` to that
directory. Do not download or copy another set. Otherwise obtain these files
from the [official SuperNEMO release](https://zenodo.org/records/20698789):

- `data_0nubb_merged.h5`
- `data_2nubb_merged.h5`
- `data_Bi214_merged.h5`
- `data_Tl208_merged.h5`

Together they occupy about 23.1 GB. Small training fractions do not reduce this
source download. The [task-owned manifest](../../../tasks/supernemo_signal_background/declared/source_files.json)
records the required sizes and official checksums.

Keep these three locations separate and outside the source checkouts:

```text
supernemo-raw/                Original four HDF5 files; never modified
supernemo-prepared/           Generated once by the preparation command
  data_*.h5                  Symbolic links to the original files
  event_indexes/             Event indexes and the partition report
  preparation.json           Records which data/tool/indexes were used
my-supernemo-project/         Your editable notebook, task and experiment
  runs/                      Results from each fresh run
  plots/                     Exported score charts
```

Prepare a **new** `PREPARED_DATA` directory:

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -B -m tutorials.supplementary.supernemo.prepare \
  --raw-data-dir "$RAW_DATA" --output-dir "$PREPARED_DATA"
```

This checks all raw-file checksums and runs the task's existing event-index
tool. It reads large columns and needs CPU time and RAM, but makes no LLM calls
and performs no GPU training. It creates links rather than copying raw files.
Success prints the path to `preparation.json`. An incomplete directory is not
ready to use; inspect the failure and choose a fresh output directory.

One local preparation of these official files took about 3 minutes 16 seconds,
peaked at 8.7 GiB RAM, and produced about 204 MiB of indexes and reports.
These are measured observations on one machine, not fixed requirements or a
speed guarantee. Allow additional memory for your other applications.

You can verify an existing preparation without rebuilding it:

```bash
.venv/bin/python -B -m tutorials.supplementary.supernemo.prepare \
  --output-dir "$PREPARED_DATA" --verify
```

The verifier reads all raw bytes again and checks the generated indexes.
Changing only repository documentation does not require rebuilding them.
The original task assigns approximately 80%/10%/10% of **events** to
train/validation/test. Search uses train and validation. The reserved test
partition is not consumed by this tutorial, which does not provide a separate
final-test launcher. Changing a fraction selects fewer events within a
partition; it does not change partition membership.

## 3. Create your editable project

Point `--data-dir` at the **prepared** directory, not the raw one:

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -B -m tutorials.supplementary.supernemo.project \
  --project "$TUTORIAL_HOME" --infra-checkout "$INFRA_CHECKOUT" \
  --data-dir "$PREPARED_DATA"
```

The project must be new and separate from both repositories and data folders.
It contains:

| Project path | What you inspect or change |
|---|---|
| `tasks/supernemo/compositions/signal_background.yaml` | Selects the task's model, data and scoring contracts |
| `tasks/supernemo/plugins/` and `declared/` | Scientific implementation and official data identity |
| `experiments/supernemo-demo.json` | Iterations, data portions, budgets and output paths |
| `experiments/workflow.json` | Fixed workflow settings |
| `llm/agents.json` | LLM provider/model routing; never API keys |
| `scripts/run-supernemo.sh` | Entry point bound to the saved experiment |
| `notebooks/supernemo_tutorial.ipynb` | Your walkthrough |
| `runs/supernemo_demo_001/` | Initial experiment's output workspace |

The task defines what the scientific problem means. The experiment chooses how
much work this run attempts. Edit these external copies; leave repository
templates and raw data unchanged. A scientifically different partition or
feature definition needs its own task identity, not an unnoticed settings edit.

New projects use the [Luna test configuration](../../shared/README.md).
Export `OPENAI_API_KEY` from your trusted external credential file into the
terminal that starts Jupyter. Keep secrets out of notebooks, JSON and scripts.
If you choose different providers, preflight identifies their required key
names. Presence checks do not prove that a provider will accept a key.

Register the exp environment's kernel and launch Jupyter from your project:

```bash
"$EXP_CHECKOUT/.venv/bin/python" -m ipykernel install \
  --prefix "$TUTORIAL_HOME/.jupyter" --name siderius-supernemo \
  --display-name "SIDERIUS SuperNEMO tutorial"
export JUPYTER_PATH="$TUTORIAL_HOME/.jupyter/share/jupyter${JUPYTER_PATH:+:$JUPYTER_PATH}"
export IPYTHONDIR="$TUTORIAL_HOME/.ipython"
export MPLCONFIGDIR="$TUTORIAL_HOME/.matplotlib"
export JUPYTER_RUNTIME_DIR="$TUTORIAL_HOME/.jupyter/runtime"
cd "$TUTORIAL_HOME"
"$EXP_CHECKOUT/.venv/bin/jupyter" lab --ServerApp.root_dir="$TUTORIAL_HOME"
```

Open `notebooks/supernemo_tutorial.ipynb` and select **SIDERIUS SuperNEMO
tutorial**. The notebook checks `TUTORIAL_HOME` and the selected interpreter.
After changing environment variables, restart Jupyter from that terminal.

## 4. Inspect, change, and run the saved experiment

Initial settings request three iterations, two rounds per iteration (Trial
then Formal), and a one-epoch ceiling. All four training/evaluation scope
fractions start at `0.01`; supported values are `0.01` through `1`. Per-epoch
`train_portion` is fixed at `1`, so it adds no further thinning.

The task balances signal and background within fixed energy bins after
selection. Consequently, `1%` does not mean exactly one percent of the final
balanced population. The notebook asks the actual task loader for illustrative
counts and displays a training event's capped/padded input.

Trial/Formal training allowances start at 2/5 minutes and 10 GiB VRAM. They
are per-attempt settings, **not whole-run spending or wall-time caps**.
Data Analysis, literature review and human advice are disabled in this
treatment. The task explicitly has no Health checks; native resource and
scoreability checks remain active.

The notebook reloads your saved JSON on Run All. Its optional save-as example,
such as `{"iterations": 4}`, writes a new experiment, script and run workspace.
Select that saved name before launching it; saving does not train anything.
Budget and data-fraction examples are shown beside the parameter table.

For the **initial** `supernemo-demo.json`, the terminal commands are:

```bash
bash "$TUTORIAL_HOME/scripts/run-supernemo.sh"
bash "$TUTORIAL_HOME/scripts/run-supernemo.sh" --dry-run
# Starts paid API calls and GPU work:
bash "$TUTORIAL_HOME/scripts/run-supernemo.sh" --launch
```

The first command inspects the saved setup; `--dry-run` also prints native
commands. Neither launches training. For a saved variant, use its own script
path printed by the notebook review cell. Launch checks keys, source pairing,
GPU readiness, raw checksums and prepared-index identity before execution.

**Run All reaches the live cell by default.** Set `RUN_QUICK_DEMO=False` to
skip it. The notebook invokes that same saved script rather than training
inside a cell. Review the displayed settings, script and workspace first.

## 5. Find and plot your results

The run directory contains native iteration records and generated models.
Its sibling `.tutorial.json` records launch inputs; notebook launches also
create `.console.log` and `.notebook-run.json`. Inspect the log and records if
a run fails. A nonzero exit retains evidence and refuses a silent restart.

Completed unchanged notebook runs reuse their results. Changes to saved inputs,
copied task code, prepared indexes or source identity require a fresh run name.
Do not edit any of these while a run is active. Independent plotting remains
available for earlier runs without credentials, data checks or another launch.

Select the earlier JSON in `PLOT_EXPERIMENT` and run the plot section. It exports
PNG, SVG and CSV from measured Formal scores. Failed scored attempts appear
hollow; missing scores are not filled with zero. For this **no-Health** task,
successful markers and CSV `validity=pass` describe scored execution, not
Health PASS. No upward trend or scientific validity is promised.

See the [task guide](../../../tasks/supernemo_signal_background/README.md) for
scientific details and the [implementation contract](implementation.md) for
technical boundaries. Return to the [tutorial index](../../README.md) to choose
another task.
