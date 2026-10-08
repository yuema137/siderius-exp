# Project8 and LIGO: run a small workflow demo

New projects use the [shared GPT-6 Luna test configuration](../../shared/README.md) for all
workflow LLM stages. It is independent of paper routing. Recorded figures below
come from earlier runs and do not establish live Luna compatibility.

These notebooks teach the same three steps as TESS and TIDMAD: **save and inspect
inputs, run the saved script, then plot real scores**. They use 512 training and
1,000 validation events for three iterations. This is a workflow demo, **not a
reproduction of the paper artifact, trained model or score**. A poor model is a
valid demo outcome; do not add iterations merely to obtain a better score.

| Tutorial | Inputs and target | Notebook |
|---|---|---|
| Project8 | Four channels: time I/Q and full complex FFT real/imaginary parts, each of length 24,576; predict electron energy in eV | [Project8 notebook](../notebooks/03_project8_tutorial.ipynb) |
| LIGO | Two whitened detector channels, cropped to 1,024 samples; predict chirp mass in solar masses | [LIGO notebook](../notebooks/04_ligo_tutorial.ipynb) |

Project8 requires both representations to contribute to the prediction. Its FFT
view uses the existing task transform; no target or extra physical measurement
is added. LIGO's small source subset uses SNR 10–15 only. Neither demo represents
the full scientific population. Validation feeds back to the agent; there is no
independent final-test step here.

## 1. Install the exact source pair

Follow [section 1 of the shared setup](../../shared/setup/README.md#1-install-the-two-exact-checkouts)
first. Keep `EXP_CHECKOUT` and `INFRA_CHECKOUT` exported. Those commands clone
[yuema137/siderius-exp](https://github.com/yuema137/siderius-exp) and
[yuema137/SIDERIUS](https://github.com/yuema137/SIDERIUS), then select the locked
infra revision. Each checkout must have its own frozen virtual environment.

Use Linux, Python 3.12 and one visible GPU supported by the frozen installation
and required accounting. Follow the [shared hardware instructions](../../shared/hardware/README.md)
for optional name expectations, capacity checks and source-pair qualification limits.
AMD/ROCm is experimental and untested; its missing driver accounting currently
prevents these tutorial launches. Intel GPU training is unsupported. This fixed workflow has no separate coding-agent
filesystem sandbox; generated models execute under your user account.

### Hardware and storage before running

Project8 and LIGO short demos each request an 8 GiB VRAM allowance. The selected
GPU needs greater physical capacity and sufficient current room under deployment
limits. Neither notebook supports CPU training. Their complete source manifests
list about 9.83 GB and 2.36 GB respectively; selected-row preparation can transfer
less, while staged arrays and run outputs need additional space. A universal
training RAM minimum has not been qualified. See the [hardware guide](../../shared/hardware/README.md).

After Quick A saves a JSON, run the hardware-only check from the exp checkout:

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -m tutorials.shared.hardware \
  --experiment "$TUTORIAL_HOME/experiments/project8_quick-demo-001.json"
```

For LIGO, use `ligo_quick-demo-001.json`; for a variant, use its actual saved
filename. No API key, training or run workspace is required. The check is a
current hardware snapshot; native model-fit checks and monitoring still apply.

## 2. Create a separate project

Choose **one** task and a new directory outside both repositories. Repeat these
steps with a different project directory for the other task.

```bash
export DEMO_TASK=project8  # Or ligo.
export TUTORIAL_HOME="$HOME/siderius-demos/$DEMO_TASK-first"
cd "$EXP_CHECKOUT"
.venv/bin/python -B -m tutorials.paper.prepared.project \
  --task "$DEMO_TASK" --project "$TUTORIAL_HOME" \
  --infra-checkout "$INFRA_CHECKOUT"
```

This copies a notebook, LLM routing and literature-search settings, plus an
initial experiment JSON and launcher. The next step creates the matching small
task/data pair. It never edits repository templates. An existing project is
never overwritten.

## 3. Download your demo data

The project created above has settings but no data. Keep that terminal open:
`EXP_CHECKOUT` must name your installed exp checkout, `TUTORIAL_HOME` your new
external project, and `DEMO_TASK` the task you selected. Replace any example
paths with your actual locations. For a first run, download the required data:

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -B -m tutorials.paper.prepared.data \
  --task "$DEMO_TASK" --project "$TUTORIAL_HOME" --download
```

The helper opens pinned release HDF5 shards through HTTPS ranges, reads selected
observations and writes small local arrays. It refuses a server that ignores
ranges rather than downloading a multi-gigabyte shard. Project8 preparation
adds the task's FFT representation to the selected time-domain observations.

Success prints `Saved task:`, `Saved data:` and row counts. The helper creates `data/demo-001/` and `tasks/<task>-demo-001/`. Initial rows
are deterministic: the first 512 training and 1,000 validation events in the
selected source ordering. The prepared arrays occupy about 595 MB for Project8
and 12.4 MB for LIGO; downloaded ranges also include HDF5 metadata and neighboring
bytes. The manifest records actual transferred bytes for the download route.
No test file is requested. Data are from the pinned
[PhyTS release](https://huggingface.co/datasets/PhyTS-team/PhyTS-bench/tree/9f203f4c338645a1e4b2c9dc7d6f820269ca5114).

Partial downloads do not verify the complete source files. Preparation records
the selected source rows and verification information for every small output
array; the launcher checks all five arrays before execution.

Before opening the copied notebook, confirm `data/demo-001/` contains
`manifest.json`, `training/{inputs,targets}.npy`, and
`evaluator/validation/{inputs,targets,loss_indices}.npy`. Its paired task entry is
`tasks/<task>-demo-001/compositions/regression.yaml`. Keep `DATA_NAME="demo-001"`
in Quick A: it saves the matching task and `data_dir` together. Inputs belong
under `data/`; `runs/` holds output. Fix missing files or a `STOP` message before
reading your data or launching. Turning off paid execution does not skip data
previews.

Do not repeat a successful preparation for every run. Reuse your downloaded
pair; occupied destinations are refused to protect earlier inputs. After an
incomplete preparation, inspect the error and use a fresh name for a retry.

To choose different row counts, pass `--train-rows` (20–2000) and
`--validation-rows` (20–1000, a multiple of 10) with a new `--name`. Then select
that new pair by setting `DATA_NAME` to your new dataset name in Quick A,
with a fresh `DEMO_NAME`. Quick A saves both its task composition and data_dir
together. For example, `--name demo-small --train-rows 64 --validation-rows 20`
corresponds to `DATA_NAME="demo-small"`, `DEMO_NAME="small-run-001"`. This 64/20
example is for offline file-editing practice: set `RUN_QUICK_DEMO=False` before
Run All. It is not a qualified live-run configuration. Re-splitting
also needs a new task/data pair; changing a Trial fraction does not re-split.

## 4. Configure keys, then start Jupyter

The default enabled agents require `OPENAI_API_KEY`. Literature Review is enabled;
human advice and Data Analysis are disabled. Change providers/models in
`llm/agents.json`; the preflight derives required key names from enabled routing.
Keys belong in the launching environment, never in notebook cells or JSON.

```bash
read -r -s -p "OpenAI API key: " OPENAI_API_KEY
echo
export OPENAI_API_KEY
export MPLCONFIGDIR="$TUTORIAL_HOME/.matplotlib"
export IPYTHONDIR="$TUTORIAL_HOME/.ipython"
"$EXP_CHECKOUT/.venv/bin/python" -m ipykernel install \
  --prefix "$TUTORIAL_HOME/.jupyter" \
  --name siderius-paper --display-name "SIDERIUS paper tutorials"
export JUPYTER_PATH="$TUTORIAL_HOME/.jupyter/share/jupyter${JUPYTER_PATH:+:$JUPYTER_PATH}"
cd "$TUTORIAL_HOME"
"$EXP_CHECKOUT/.venv/bin/jupyter" lab --ServerApp.root_dir="$TUTORIAL_HOME"
```

Select **SIDERIUS paper tutorials**. Open `03_project8_tutorial.ipynb` or
`04_ligo_tutorial.ipynb` in your project, then Run All. Quick A saves or verifies
the named experiment; Quick B executes its script; Quick C saves PNG/SVG/CSV results.
For a key changed after Jupyter started, restart the server from the configured
terminal; a kernel restart alone does not update the server's environment.

The per-attempt training budgets do not bound notebook duration. Each iteration also calls LLMs and searches literature. Provider latency and literature-service rate limits can add several minutes per iteration; the console log shows progress and retries. With the defaults shown here, our RTX 5090 runs completed all three iterations in about 32 minutes for Project8 and 29 minutes for LIGO, including service waits and native retries. These are observed examples, not duration guarantees. Both runs produced negative R² scores; the demo teaches execution and inspection rather than scientific performance.

## 5. Know exactly what runs and where files go

For Project8's default `DEMO_NAME="quick-demo-001"`:

```text
$TUTORIAL_HOME/
  notebooks/03_project8_tutorial.ipynb
  tasks/project8-demo-001/compositions/regression.yaml
  tasks/project8-demo-001/declared/prepared.json
  tasks/shared/                             # copied task adapter/metric code
  data/demo-001/manifest.json                # row membership, source and integrity record
  data/demo-001/training/{inputs,targets}.npy
  data/demo-001/evaluator/validation/{inputs,targets,loss_indices}.npy
  experiments/project8_quick-demo-001.json    # Quick A's saved settings
  llm/{agents.json,literature_review.yaml}
  advice/README.txt                          # explains why advice is inactive
  scripts/run-project8_quick-demo-001.sh      # exact execution entrypoint
  runs/project8_quick-demo-001/               # native records and models
  runs/project8_quick-demo-001.console.log
  runs/project8_quick-demo-001.notebook-run.json
  plots/project8_quick-demo-001/              # score-versus-iteration PNG/SVG/CSV
```

For LIGO, substitute `ligo` and notebook `04_ligo_tutorial.ipynb`. Quick A prints
absolute paths and reloads saved settings. Review the task entry, data manifest,
experiment JSON, LLM configuration and shell script before Quick B.

The terminal equivalent is:

```bash
# Preview only. Run this after Quick A saved the files.
bash "$TUTORIAL_HOME/scripts/run-${DEMO_TASK}_quick-demo-001.sh"
# Execute the saved experiment, instead of clicking Quick B.
bash "$TUTORIAL_HOME/scripts/run-${DEMO_TASK}_quick-demo-001.sh" --launch
```

Do not launch both ways for the same demo. Notebook and script fail before API
calls/training if keys, data, environments, pins or CUDA setup are missing.
Presence of a key does not prove provider authentication or available credit.
Budgets limit training attempts, not total LLM time or spending.

The plot keeps the existing paper style. These two task compositions explicitly
set `task_health: {none: true}`: filled markers mean successful scored execution
under that declaration, **not Health PASS**. Failed scored attempts are hollow;
missing scores remain missing in CSV. Very small demos may return negative R².
The current-best line can include invalid points, as in the other tutorials.

Optional notebook cells demonstrate four iterations, changed Trial/Formal
fractions, separate VRAM budgets and a new event split. They save files only
when enabled and print the exact command to run each saved variant. They do not
silently launch another search. Keep all inputs and outputs in your project.

## Small data still needs enough batches

The default uses 512 training events, batch size 1 and full per-epoch exposure
inside the selected scope. A 50% Trial has 256 batches per epoch. The 1,000-event
validation pool fixes 100 events for epoch-loss monitoring; four epochs provide
up to 400 validation observations. These counts give the native runtime verifier
more real observations; it still decides whether timings are stable enough.

The large validation-to-training ratio serves timing measurement in this short
demo, not a recommended scientific split. Reducing data or fractions, increasing
batch size, or reducing epochs can leave too little evidence and cause rejection
before scoring. A custom 64/20 dataset is for offline file-editing practice.

Project8 retains a partial final training batch. LIGO keeps native `drop_last`
behavior, which can discard a partial tail after a custom batch-size change;
batch size 1 has no partial tail. No Health threshold, training allowance or
runtime verification rule is relaxed.
