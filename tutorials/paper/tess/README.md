# TESS: run three iterations, then change your experiment

Predict a star's rotation frequency from its brightness measurements. This guide
creates a small external project, prepares the released training/validation data
and runs the [TESS notebook](../notebooks/01_tess_tutorial.ipynb). The notebook
saves configuration; a separate shell script runs SIDERIUS.

Browse the [real data and recorded results](../examples/README.md) first.
This is a process demo, not a paper artifact reproduction or a promised score.
The archived example keeps its original model/source identity; new projects use
the [Luna test profile](../../shared/README.md).

## 1. Install and check the hardware requirements

Complete the [shared environment and key setup](../../shared/setup/README.md).
Keep `EXP_CHECKOUT`, `INFRA_CHECKOUT` and the provider keys exported in the same
terminal. You need a supported NVIDIA GPU for training. CPU/Intel training is
unsupported; AMD/ROCm is experimental and lacks required accounting.

The quick demo requests an 8 GiB VRAM allowance, not a measured model minimum.
The card must have greater capacity and sufficient current room under its limits.
Read the [hardware guide](../../shared/hardware/README.md). A universal training
host-RAM minimum has not been qualified. Allow about 31 MB for source downloads,
18 MB for staged NPZ data, plus environments, checkpoints and logs.

TESS's NoPrior workflow disables human advice, Data Analysis and literature
review. Default routing needs `OPENAI_API_KEY`, not a Semantic Scholar key.
Keys belong in your launching environment, never in the notebook or routing JSON.

## 2. Create your external project and its kernel

Use your installed checkout paths from section 1 and choose a **new project
directory outside both repositories**. Replace every `/absolute/...` example
with your own path. Do not create the project directory beforehand: initialize
it now, before downloading data. The initializer refuses an existing project.

```bash
export EXP_CHECKOUT="/absolute/path/to/siderius-exp"
export TUTORIAL_HOME="/absolute/path/to/my-tess-project"
export PYTHONDONTWRITEBYTECODE=1
cd "$EXP_CHECKOUT"
.venv/bin/python -B -m tutorials.paper.project \
  --project "$TUTORIAL_HOME" --infra-checkout "$INFRA_CHECKOUT"
"$EXP_CHECKOUT/.venv/bin/python" -B -m ipykernel install \
  --prefix "$TUTORIAL_HOME/.jupyter" --name siderius-exp-tutorial \
  --display-name "SIDERIUS exp tutorial"
export JUPYTER_PATH="$TUTORIAL_HOME/.jupyter/share/jupyter"
export IPYTHONDIR="$TUTORIAL_HOME/.ipython"
export MPLCONFIGDIR="$TUTORIAL_HOME/.matplotlib"
export JUPYTER_RUNTIME_DIR="$TUTORIAL_HOME/.jupyter/runtime"
```

Initialization copies your notebook, task package, initial experiment and Luna
routing. It downloads no data and calls no provider. Keep this terminal open.

```text
YOUR_PROJECT/
├── project.json                   paths to the installed checkouts
├── notebooks/01_tess_tutorial.ipynb
├── tasks/tess/                    scientific task package
├── experiments/                   saved experiment JSON files
├── llm/agents.json                 model routes; NO keys
├── scripts/                       saved launch entrypoints
├── data/                          source/staged data or external references
├── runs/                          one new output workspace per run
└── plots/                         score plots and CSV records
```

The task defines inputs, target, data split and scoring. **Health checks** are
task-defined tests that can reject an output, such as nearly constant predictions,
even when training succeeded. An experiment selects that task and its data/routing,
then sets iteration counts,
fractions and budgets. Editing a notebook variable changes nothing on disk until
its save cell writes the JSON used by the script.

Each iteration proposes a candidate model. **Trial** tries training settings;
**Formal** evaluates the chosen configuration with its declared data and budgets.
Both use workflow validation; Formal is not an untouched final test.

## 3. Download and prepare data once

The initialized project contains settings, not the dataset. In the same terminal,
run this first-time preparation with two new directories inside your external
project:

```bash
export TESS_DATA="$TUTORIAL_HOME/data/tess-data"
cd "$EXP_CHECKOUT"
.venv/bin/python -m tutorials.paper.prepare_tess \
  --raw-dir "$TUTORIAL_HOME/data/raw-tess" \
  --data-dir "$TESS_DATA"
```

The helper downloads `tess_regression_train.parquet` and
`tess_regression_val.parquet` from the pinned
[PhyTS release](https://huggingface.co/datasets/PhyTS-team/PhyTS-bench/tree/9f203f4c338645a1e4b2c9dc7d6f820269ca5114/TESS/split),
verifies them against the [source declaration](../configs/tess_source.json), and
converts them to the two run inputs: `tess_rotation_train.npz` and
`tess_rotation_val.npz`. Allow about 31 MB for originals and 18 MB for these NPZ
files, plus run outputs. This stages 3,338 training and 442 validation curves;
the 403 held-out test curves are not downloaded or used. No Hugging Face token
is needed.

After success, both NPZ files must be in `TESS_DATA`. The initial
`experiments/tess-experiment.json` saves that default directory as `data_dir`;
`runs/` is for output. Changing an environment variable does not update the JSON.
If you choose another destination, update `data_dir` before the first notebook
code cell and Quick A.

The helper refuses occupied destinations. If preparation fails, stop, inspect
the error and choose new destinations for a retry; do not treat partial output
as ready. Quick A lists required files as `FOUND` or `MISSING`: fix missing or
mismatched data before plotting. File presence and the script preview are not
full verification; launch performs the data check.

**Already completed this setup on your machine?** Keep the matching NPZ pair
and saved `data_dir`; skip downloading. The notebook's later advanced data-entry
cell is optional and does not require another preparation. Fraction controls
sample within the saved split; they do not change which stars belong to validation.

## 4. Open your notebook and inspect Quick A

From the same terminal with keys and kernel settings exported:

```bash
cd "$TUTORIAL_HOME"
"$EXP_CHECKOUT/.venv/bin/jupyter" lab --ServerApp.root_dir="$TUTORIAL_HOME"
```

Open `notebooks/01_tess_tutorial.ipynb` and choose **SIDERIUS exp tutorial**.
For a cautious first pass, set `RUN_QUICK_DEMO=False` in Quick A. Run through
Quick A to save and review the exact demo files, and inspect a real training curve.
No API/GPU training starts with that switch off; preparation cells can save files.
The real-data preview still reads local NPZ files, so fix Quick A data errors
before proceeding to it.

The default `DEMO_NAME="quick-demo-001"` saves this pair:

```text
experiments/tess_quick-demo-001.json   actual three-iteration settings
scripts/run-tess_quick-demo-001.sh     reads that exact JSON
runs/tess_quick-demo-001/              created only by execution
plots/tess_quick-demo-001/             PNG, SVG and CSV after plotting
```

These differ from the initializer's `tess-experiment.json` / `run-tess.sh`,
which describe a separate one-iteration manual example. Use the **Quick A pair**
for this guide. Review its paths, task, `llm/agents.json`, fractions and budgets.
Quick A creates the named demo or verifies that its saved settings still match,
then reads it back for a checklist and exact shell commands. To change an existing
demo, use the saved-variant lesson in section 6 instead of overwriting its JSON.

After saving, check that same JSON from an exp terminal without provider calls:

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -m tutorials.shared.hardware \
  --experiment "$TUTORIAL_HOME/experiments/tess_quick-demo-001.json"
```

This queries current GPU readiness and runs a tiny kernel. It does not reserve
memory or prove the future model fits. Fix any **STOP** or missing-item errors
before proceeding. Launch repeats source, data, credential and GPU checks.

## 5. Run once, then read the plot

Choose one route, **not both**:

- **Notebook:** change `RUN_QUICK_DEMO=True` in Quick A and **rerun Quick A**
  to update the kernel variable, then run Quick B and Quick C. Or use Run All
  after changing that flag. Quick B invokes the saved script; Quick C plots it.
- **Terminal:** preview the same saved script, then deliberately add `--launch`:

```bash
bash "$TUTORIAL_HOME/scripts/run-tess_quick-demo-001.sh"
# Paid LLM calls and GPU training:
bash "$TUTORIAL_HOME/scripts/run-tess_quick-demo-001.sh" --launch
```

Preview needs no API request, prepared data or GPU; it checks source pins,
routing and composition. Key presence is not provider authentication. A launch
uses three search iterations and a five-epoch ceiling per attempt; one iteration
can contain Trial, Formal and retries. Training budgets are per attempt, not a
total wall-clock/API cap. LLM work can dominate elapsed time.

Keep the notebook kernel or launching terminal running. Results and generated
models go into the workspace shown above. Notebook execution also writes sibling
`.console.log` and `.notebook-run.json` files; direct shell output stays in its
terminal. Native launch receipts use the sibling `.tutorial.json` file.

Quick C writes score-versus-iteration PNG, SVG and CSV under `plots/`. TESS uses
R², higher is better, on workflow validation—not the held-out test set. Failed
scored attempts are hollow; missing scores are not zero. The current-best line
can include invalid scores, so inspect Health and native records as well.
A high score or Health PASS is not required to demonstrate the process.

An unchanged completed notebook run reuses its records without new API calls.
To plot another run, set Quick C's `PLOT_WORKSPACE` to its absolute directory
and execute **only that plotting cell**. An interrupted or changed run requires
inspection and a fresh identity; do not erase the old evidence to force reuse.

## 6. Change the saved experiment

After Quick C, **Change the demo you just ran** reads the actual saved JSON.
Set `SAVE_CHANGED_DEMO=True` once and use a new name, for example
`quick-demo-four-001`. The example changes three iterations to four, preserving
other saved fields and producing:

```text
experiments/tess_quick-demo-four-001.json
scripts/run-tess_quick-demo-four-001.sh
runs/tess_quick-demo-four-001/          new result destination
```

Saving selects the new pair for review but **does not launch a second run**.
Use the displayed preview/launch commands when ready. The task/data remain
shared references; they are not copied or re-split by an iteration change.

On a later session, set `RUN_QUICK_DEMO=False`, select
`SELECTED_DEMO_NAME="quick-demo-four-001"` in that lesson and leave
`SAVE_CHANGED_DEMO=False`. Follow its bootstrap/selection/review instructions.
After running, set Quick C's plot workspace to the newly printed result path.

The remaining notebook exercises are separate, optional examples:

| Change | Where to learn it |
|---|---|
| Iterations, epochs, data fractions or Trial/Formal budgets | Advanced Demos 1–3; save with `WRITE_DEMOS` |
| New whole-star train/validation membership | Demo 4, `MAKE_NEW_SPLIT`; creates a matching new task/data pair |
| GPU selection and memory allowance | [Hardware guide](../../shared/hardware/README.md) |
| Research or custom LLM routing | [Configuration levels](../../shared/README.md) |

These advanced examples start from the initial configuration, not your modified
quick-demo JSON. Changing a split changes the scientific protocol; preserve whole
stars and the untouched test set. The copied advice example is inactive in
NoPrior: `advice_file` must remain null. This guide has no separate final-test path.

Generated model code runs in framework subprocesses under your user account;
this fixed workflow is not an OS sandbox against malicious code. Keep unrelated
sensitive files out of the run area. See the [technical contract](../implementation.md)
for execution/receipt details, and [paper artifacts](../../../experiments/paper-artifacts.md)
for historical reproduction rather than a new demo run.
