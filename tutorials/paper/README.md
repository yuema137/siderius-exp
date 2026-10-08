# Paper tutorials: configure a scientific task and launch your own run

**See the workflow before installing:** the [notebooks](notebooks/README.md) now
include real training-sample figures and recorded three-iteration result plots.
The [example gallery](examples/README.md) lists scores, provenance and limitations.
These archived examples stay separate from results produced by your own run.

Use these tutorials to learn **which files define a task, which parameters define
an experiment, and which terminal command runs what you saved**. You work in your
own project directory. The notebook explains and saves configurations; a separate
shell script launches the fixed workflow and writes results into that project.

## Choose a tutorial

| Tutorial | Scientific question | What you can change | Start here |
|---|---|---|---|
| **TESS** | Predict a star's rotation frequency from its brightness measurements over time | Iterations, epochs, Trial/Formal fractions, time/VRAM budgets, and a new whole-star train/validation split | **[Open the TESS notebook](notebooks/01_tess_tutorial.ipynb)**; follow setup below before executing your own copy |
| **TIDMAD, band 0–3** | Recover an injected waveform from noisy detector measurements | The same budgets/fractions, plus file-index training/validation/final-test groups | **[TIDMAD setup and walkthrough](tidmad/README.md)** · **[Open the TIDMAD notebook](notebooks/02_tidmad_tutorial.ipynb)** |
| LIGO | Predict chirp mass from two detector channels | Small-data preparation, iteration/budget/fraction controls and new event splits | [Setup](prepared/README.md) · [LIGO notebook](notebooks/04_ligo_tutorial.ipynb) |
| Project8 | Predict electron energy using time/frequency four-channel inputs | Small-data preparation, iteration/budget/fraction controls and new event splits | [Setup](prepared/README.md) · [Project8 notebook](notebooks/03_project8_tutorial.ipynb) |

For the underlying TESS task and data contract, see the
[TESS task package](../../tasks/phyts_tess/README.md). The tutorial downloads its
pinned [PhyTS TESS data](https://huggingface.co/datasets/PhyTS-team/PhyTS-bench/tree/9f203f4c338645a1e4b2c9dc7d6f820269ca5114/TESS/split),
or reuses the shared machine's existing files.

## Browse this directory

- [notebooks/](notebooks/README.md): all four walkthroughs and their setup routes.
- [configs/](configs/README.md): TESS template and pinned download declaration.
- [scripts/](scripts/README.md): the generic TESS runner wrapper; generated user scripts live in your external project.
- [tidmad/](tidmad/README.md): TIDMAD setup, file splits and separate final testing.
- [prepared/](prepared/README.md): Project8/LIGO setup, small datasets and event splits.

## What these tutorials can—and cannot—do

You can use them to prepare data, configure model/provider routing without saving
keys, save a task/experiment variant, check its actual files and parameters, run
it on a supported GPU, and inspect the resulting records. Quick A in each notebook shows the saved-file checklist and exact preview/launch
commands for the experiment you select. TESS and TIDMAD also include an advanced
**Before you run** section.

These are **learning and execution demos**, not a claim of complete paper
reproduction. All four tasks have notebooks. Fresh LLM
searches may produce different models and scores. The demos do not reproduce
the paper's coding-agent/orchestration comparisons or retrospective reviews.
Archived-checkpoint replay and the original campaign launchers are separate
routes. The [paper artifact reference](../../experiments/paper-artifacts.md)
connects frozen configurations, original source pairs and archived evidence;
it also records missing provenance. Changing a split defines a new scientific protocol.

The TESS and TIDMAD three-iteration notebooks have been run end to end on an RTX 5090: about
24 minutes for TESS and 35 minutes for TIDMAD. These times include LLM work,
not just training; your run may take longer or shorter. The separate, optional
TIDMAD final-test example has not yet completed a successful end-to-end run.

## What you will see after Run All

This demo teaches the complete workflow; it does not aim to produce a model
that passes Health checks. An invalid score is a real result: it appears as a
hollow marker. Do not add iterations or change checks just to obtain a filled point.

With the external project, data and exported keys ready, the notebook saves a
three-iteration experiment, displays its files/parameters, invokes its shell
script, and draws **score versus iteration** from actual run records. For TESS
and TIDMAD, filled markers mean Health PASS and hollow markers mean Health
FAIL/failed attempts. Project8 and LIGO explicitly declare no task-specific
Health checks: filled markers mean successful scored execution under that
declaration, not Health PASS; failed scored attempts remain hollow.
The plot follows the paper: dashed Formal results, a solid current-best line,
and stars for new bests that meet the task's applicable validity policy. TESS uses boundary triangles for
negative R² values, as do Project8 and LIGO; TIDMAD displays its denoising score at its actual value,
including negative values. Missing scores stay in the CSV. The current-best
line can include invalid points. CSV, PNG and SVG outputs are saved under your
project's `plots/`.

Before a new run, the notebook and script check the checkout Python environments,
required input files and exported API key names. Errors list missing items and
repair steps. Launch additionally checks source pins, data integrity and the
selected visible GPU through the framework environment. Export keys **before starting Jupyter**;
restart its server from that terminal after changing the environment. Key presence
does not verify provider authentication or credit.

Re-running an unchanged completed demo redraws results without another API call.
To plot a different run, change `PLOT_WORKSPACE` in TESS/TIDMAD or
`PLOT_EXPERIMENT` in Project8/LIGO, then execute only the plotting cell. To launch changed settings, choose a new `DEMO_NAME`. Three iterations can
still take many minutes because each includes LLM work and native checks; small
budgets do not guarantee a valid model. Independent final testing is a separate,
manual model-selection step in TIDMAD, not part of any quick-demo validation plot.

## Before you start

All four quick demos begin with an 8 GiB VRAM allowance. That is a configured
limit, not a measured minimum: capacity, current occupancy and deployment limits
all matter. Read the [per-task hardware guide](../shared/hardware/README.md)
before downloading large data or attempting training on a small machine.
After Quick A saves your experiment, check that exact JSON without paid calls:

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -m tutorials.shared.hardware \
  --experiment "$TUTORIAL_HOME/experiments/tess_quick-demo-001.json"
```

Replace the filename with `tidmad_quick-demo-001.json`,
`project8_quick-demo-001.json` or `ligo_quick-demo-001.json` for the selected
notebook, or the actual variant you saved. The command checks hardware fields
only, needs no API key and creates no run workspace. Fresh launches repeat GPU
checks before provider calls. A passing snapshot neither reserves VRAM nor
guarantees that a generated model fits.

- Linux, Python 3.12, `git`, `uv`, and one visible GPU supported by the frozen
  PyTorch installation and required resource accounting. NVIDIA model names are
  not restricted. AMD/ROCm is experimental and untested; its missing driver
  accounting currently prevents this protected tutorial route. Intel GPU and
  CPU training are unsupported.
- Access to the selected LLM providers and exported API keys. Runs can incur
  charges. Training budgets do not cap total script duration or API spending.
- Two installed source repositories plus a **third, separate directory** for
  your editable project, data references and results. No tutorial step asks you
  to edit source-repository task templates.
- Prepared data: TESS downloads about 31 MB and stages about 18 MB of NPZ inputs;
  TIDMAD uses eight large HDF5 files for one band. Reuse existing shared files
  when available instead of downloading again.

The public release sources are [yuema137/siderius-exp](https://github.com/yuema137/siderius-exp)
and [yuema137/SIDERIUS](https://github.com/yuema137/SIDERIUS). During pre-release,
these repositories may require access; the commands below target that release
pair. Development PRs are not the public installation source.

**Reading order:** install the exact source pair in section 1. For TESS, continue
through sections 2–5, then follow Quick A → B → C in your copied notebook.
Its **Before you run** checklist is for optional advanced/manual runs. For TIDMAD, continue with the [TIDMAD guide](tidmad/README.md) after
section 1. For Project8 or LIGO, continue with the [small-data guide](prepared/README.md).
The commands in the remaining sections of this page are TESS examples.

## Task package, experiment, notebook and script

The **task package** owns the scientific problem: data identities and splits,
input/output contract, metric and validity rules. An **experiment** selects
that task plus a workflow/treatment, then specifies model routing, budgets,
hardware and run locations. For example, increasing epochs changes the
experiment; changing the target or metric changes the task.

The notebook explains both layers and demonstrates editing a copied task and
saving an external `tess-experiment.json`. The script reads that saved file,
resolves the selected task, checks prerequisites and launches the framework.
The quick-demo Run All cell invokes that saved script; training and provider
calls remain in the existing workflow. Its in-memory edits do not affect a
script until saved to the file passed with `--experiment`.

`TutorialExperiment` is this teaching entrypoint's input contract, not a new
repository-wide experiment format. It selects a task using `composition` and
model routing using `llm_config`; the CLI requires explicit external copies. The
workflow and NoPrior treatment are fixed by this entrypoint. To teach another
workflow/treatment, define and qualify its experiment entrypoint explicitly.

## 1. Install in the two exact checkouts

Use Linux and Python 3.12 with the exact paired framework and experiment
revisions. The current frozen installation selects CUDA packages. A different
NVIDIA device may work when its driver and this PyTorch build support it; the
launcher checks that combination before starting the run. The historical TESS
deployment used RTX 5090 with an 8 GiB model budget. That record does not qualify
a new device or backend.

The pinned source pair passed offline installation, historical prompt checks
and fresh-project command previews. Those checks do not establish that a real
run will succeed on your GPU. Public-source installation is verified separately
after release synchronization; do not bypass a missing revision or the pin check.
See the [qualification record](../../provenance/validation/2026-10-08_final_source_pair.md)
for the tested scope.

Choose a new location for the public exp checkout:

```bash
export EXP_CHECKOUT="/absolute/path/to/siderius-exp"
git clone https://github.com/yuema137/siderius-exp.git "$EXP_CHECKOUT"
cd "$EXP_CHECKOUT"
uv sync --python 3.12 --group dev --group tutorial --frozen

# Choose a NEW sibling checkout, outside the exp checkout.
export INFRA_CHECKOUT="/absolute/path/to/SIDERIUS-tutorial"
git clone https://github.com/yuema137/SIDERIUS.git "$INFRA_CHECKOUT"
git -C "$INFRA_CHECKOUT" checkout --detach "$(cat "$EXP_CHECKOUT/SIDERIUS_REVISION")"
(cd "$INFRA_CHECKOUT" && uv sync --python 3.12 --group dev --frozen)
```

The exp environment runs notebooks and preparation tools; the infra
environment executes the research loop. Neither borrows the other's
`site-packages` or uses `PYTHONPATH`. Both source checkouts must be clean at
preview/launch time. Do not edit the version pin to work around a refusal.

New projects copy the independent [test LLM profile](../shared/README.md),
which selects GPT-6 Luna for every workflow LLM route and explicitly selects
`native-timing-v1`. It does not borrow paper routing or historical prompts.
This native planner is built into infra; no historical planner package is needed.
Preview resolves its identity in both environments and records it in the receipt.
If the identities disagree, restore the paired revisions and environments before
retrying. These checks are offline; they do not prove your account can call Luna.

Existing user projects are not rewritten. To upgrade one, create a fresh project
and a fresh run workspace, then transfer your intended parameter edits. Do not
resume an old workspace with the new infra pin.

## 2. Configure keys without storing them in a notebook

The shipped TESS NoPrior treatment disables advice, Data Analysis **and
literature review**. Active agents use OpenAI routing, so it needs
`OPENAI_API_KEY`; it needs no Semantic Scholar key. Changing to another
supported provider changes the required keys. Preview lists their names.

In the terminal that will launch the run:

```bash
read -r -s -p "OpenAI API key: " OPENAI_API_KEY
echo
export OPENAI_API_KEY
```

This reads without terminal echo and does not put the value in shell history.
For repeated use, load a trusted external mode-600 environment file into the
same launching shell. Do not enter keys in notebook cells, experiment JSON,
command arguments or Git. A key in the Jupyter server is not thereby present
in a separate terminal.

**Start Jupyter from the configured terminal.** If its server was already
running, stop and restart the server from that terminal, then restart the
kernel. Restarting only a kernel does not update the server's environment.
The notebook and script preview report each required variable's name and
presence, and warn when any are missing. `--launch` refuses missing or
whitespace-only values before contacting providers. Merely creating a local
credential file does not export its contents. Neither check prints key values.
These checks use the selected routing, including an external routing file.

The tutorial model is GPT-6 Luna. Inspect all routes in your project's
`llm/agents.json` before launching. If you choose another available model, make
that change in your external copy and start a fresh run. See the
[configuration levels](../shared/README.md) before increasing model cost.
Key presence does not prove provider access; only a request can.

## 3. Create your own project and register its notebook kernel

Source checkouts supply installed code and templates. **Do not edit their
notebooks, scripts, task packages, experiments or LLM configuration.** The
`.venv` created during installation is environment infrastructure, not a place
for your experiment files. All tutorial edits and outputs go to a separate
user project. A run workspace is just one output directory within that project.

```text
/path/to/SIDERIUS-tutorial/           installed infra; source unchanged
/path/to/siderius-exp/               installed exp; source unchanged
/path/to/my-tess-project/            YOUR editable project (TUTORIAL_HOME)
├── project.json                    paths to the two installed checkouts
├── notebooks/01_tess_tutorial.ipynb  your editable notebook and saved outputs
├── tasks/tess/                      your complete task-package copy
├── experiments/tess-experiment.json your initial experiment
├── llm/agents.json                  model/provider routing; NO API keys
├── advice/human_advice.example.json inactive example for this NoPrior demo
├── scripts/run-tess.sh              your initial editable launch script
├── data/raw-tess/                   downloaded Parquet and source receipt
├── data/tess-data/                  exactly the two run-input NPZ files
├── runs/tess-demo-001/              created by launch; logs/models/results
├── runs/tess-demo-001.tutorial.json launch receipt
└── .jupyter/                       local kernel registration
```

Keep credentials separately, for example in a trusted mode-600 file under your
user configuration directory. Export them as described in section 2. Never
copy them into the project, its scripts, notebook outputs or routing JSON.

Choose a **new** directory outside both repositories. Initialization copies
inputs and generates the launch script; it makes no API call and downloads no
data. It refuses an existing directory so it cannot overwrite your work.

```bash
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

The kernel is now registered as **SIDERIUS exp tutorial**. Prepare data in
section 4 before starting Jupyter in section 5. Keep this terminal open so
Jupyter inherits `TUTORIAL_HOME`, the kernel settings and your exported keys.

### Where human advice belongs

Human advice is a scientific input, not an API credential. The initializer
copies the existing structured JSON example into
`advice/human_advice.example.json`. **NoPrior does not read this file.**
`advice_file` must remain `null`; selecting a file is refused, not silently
ignored. Editing this example alone cannot affect a run.

An advice-enabled experiment needs its own information-treatment identity,
explicit advice path/digest and framework advice routing. This tutorial has
not implemented that different treatment. Do not add advice to the frozen
NoPrior experiment or put it in `llm/agents.json`. Keep a future active advice
artifact under your project's `advice/` directory and bind it through that
separately defined experiment.

## 4. Choose existing data OR a download

If you already have the pinned source files, set `TESS_SOURCE` to their absolute
external directory and reuse them instead of downloading:

```bash
export TESS_SOURCE="/absolute/path/to/TESS/split"
cd "$EXP_CHECKOUT"
.venv/bin/python -B -m tutorials.paper.data_entry --task tess \
  --project "$TUTORIAL_HOME" --source "$TESS_SOURCE"
```

This verifies the pinned Parquet files and writes only the two required NPZ run
inputs (about 18 MB). Raw Parquet is neither downloaded nor copied. If a verified
NPZ directory already exists, set your saved experiment's `data_dir` to that
absolute path and reuse it without staging again. Do not expose the test split.

On another machine, use the download option below instead. Run from exp:

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -m tutorials.paper.prepare_tess \
  --raw-dir "$TUTORIAL_HOME/data/raw-tess" \
  --data-dir "$TUTORIAL_HOME/data/tess-data"
```

Both destinations must be new. This downloads about 31 MB from the pinned
[PhyTS dataset revision](https://huggingface.co/datasets/PhyTS-team/PhyTS-bench/tree/9f203f4c338645a1e4b2c9dc7d6f820269ca5114/TESS/split),
checks the source hashes in [tess_source.json](configs/tess_source.json), then
calls the task's staging tool. Expected result: 3,338 training and 442
validation curves in two NPZ archives. The 403 held-out test curves are not
downloaded. No Hugging Face token is needed for the public files.

If a download fails, inspect the error and choose new destinations for a retry;
the helper never overwrites existing data. It does not re-split stars. Changes
to the population need a new task identity and separate qualification.

## 5. Run the notebook demo, or launch an advanced example

After completing keys, project/kernel setup and data preparation, start Jupyter
from the same terminal:

```bash
cd "$TUTORIAL_HOME"
"$EXP_CHECKOUT/.venv/bin/jupyter" lab --ServerApp.root_dir="$TUTORIAL_HOME"
```

Open `notebooks/01_tess_tutorial.ipynb` and select **SIDERIUS exp tutorial**.
For your first run, use **Run All**: Quick A saves/checks the demo inputs, Quick B
runs its script, and Quick C plots the results. You can stop at the plot. You do
not also need to run a terminal command. `RUN_QUICK_DEMO=False` skips API/GPU
execution, but Quick A still saves inputs. Completed unchanged runs are reused.

**Optional advanced/manual route:** continue below only when you want to save
and launch a different example. Each has its own JSON, script and result folder;
it does not change the quick demo you just ran.

In the notebook, use **Before you run: one experiment, one checklist, one launch
command** after saving your edits. Select one example; its report reloads the
experiment JSON, checks the script binding, lists task/routing/data files, and
shows effective budgets and exact commands. If you edited a demo, use that
demo’s command—not the initial launcher below.

Initialization already created an experiment with explicit paths to your task
copy, your LLM routing and `runs/tess-demo-001`. From **any terminal directory**:

```bash
bash "$TUTORIAL_HOME/scripts/run-tess.sh"

# Starts paid API calls and model training:
bash "$TUTORIAL_HOME/scripts/run-tess.sh" --launch
```

After the quick demo, four advanced exercises explain individual changes.
Each starts from the initial experiment so you can understand its effect independently.

| Demo | Edit | Effect |
|---|---|---|
| Search longer | `iterations=3`, `epochs=10` | Up to three candidate cycles, up to ten training passes per attempt |
| Smaller Trial | `trial_train_fraction=0.25`, `trial_val_fraction=0.5`; Formal fractions stay `1.0` | Less data within the same split; Formal still uses full train/validation |
| Resource allowance | `trial_minutes=3`, `formal_minutes=10`, `trial_vram_gib=6`, `formal_vram_gib=8` | Separate per-attempt limits; not a total script time/cost cap |
| New split | `validation_fraction=0.2`, `seed=42` | Regroup released train+validation by whole stars into a new task/data pair |

For the first three demos, enable `WRITE_DEMOS` to save experiment JSONs and
scripts. For example, run the saved smaller-Trial example:

```bash
bash "$TUTORIAL_HOME/scripts/run-less-trial-data.sh"
bash "$TUTORIAL_HOME/scripts/run-less-trial-data.sh" --launch
```

Its saved experiment is `experiments/less-trial-data.json`, and its output is
`runs/demo_less_trial_data/`. Changing a Python variable without saving does
not change the script's next run. The initialized project fixes both Trial
fractions at `1.0`; `null` explicitly delegates a Trial fraction to the agent.
You set the Formal training and validation fractions separately.

Demo 4 has a separate `MAKE_NEW_SPLIT` switch. It creates
`tasks/tess-split-seed42/`, `data/tess-split-seed42/`, a new manifest and split
receipt, `experiments/new-split.json`, and `scripts/run-new-split.sh`. The script
writes results under `runs/demo_new_split/`. The test split is never used.
This is a new scientific task variant: do not compare its score directly with
paper scores or reuse a model trained on stars now in validation. The helper
verifies the copied manifest, data keys, preserved curves and star grouping;
that does not qualify the new split's scientific performance.

The run directory holds framework records, generated models/plugins and
calibration artifacts. Its sibling `.tutorial.json` stores the launch receipt.
Terminal output is displayed in your terminal; to keep a console log too:

```bash
bash "$TUTORIAL_HOME/scripts/run-less-trial-data.sh" --launch \
  > "$TUTORIAL_HOME/runs/demo_less_trial_data.console.log" 2>&1
```

Choose a fresh run name/workspace before another launch. Do not save editable
inputs inside `runs/<name>/`: the framework requires that run directory not
yet exist. Input files and notebook checkpoints belong in their project
folders. Jupyter/plot caches above stay in the project; package installation
caches follow your normal `uv` configuration outside tracked source.

The script has explicit `EXP_CHECKOUT` and `EXPERIMENT` bindings. Edit your
script to choose another saved experiment. If you move the project or installed
checkouts, update `project.json`, script bindings and all absolute paths in
experiment JSON; moving files alone does not rebind references.

Preview validates source pins, routing and composition and prints JSON. It
needs no credentials, prepared data or GPU. Launch additionally checks keys,
both staged populations, hashes, selected GPU properties, required accounting
capability and a tiny kernel in infra's environment. It refuses root execution.

The initial manual experiment (distinct from the three-iteration Run All demo) runs one iteration with one Trial and one Formal opportunity,
one-epoch ceilings, 2/5-minute training attempt budgets and an 8 GiB VRAM budget. A
candidate can fail validation or training; a Formal score is not guaranteed.
Explicit data fractions can differ from the historical agent-controlled Trial
smoke run described below.
Proposal reasoning, generated-code implementation and planning make separate
LLM requests before training. Even this one-iteration example may take much
longer than the training budget. Attempt budgets are not a total wall-clock
or API-spend cap. This teaching
entrypoint has no six-hour campaign supervisor.

A tiny Trial may fail runtime calibration before a score exists. In the
RTX 5090 smoke test, the first attempt provided only 2 training batches and
1 validation batch. The workflow retried with full scopes and batch size 4,
then produced a score. That observed recovery is not guaranteed for every
new LLM proposal. One epoch can also produce near-constant predictions;
inspect task Health and the result authority instead of treating a finite
score as scientific success. Do not disable admission or Health to force a pass.

The sibling `<workspace>.tutorial.json` records settings, command, revisions,
composition identity, routing digest and data digests without secrets. Node
records live under the workspace. The notebook shows how to inspect them.
A high score is not a demo pass rule: inspect exit status and failure records.
The terminal owns the run. Use its interrupt/stop mechanism, then inspect the
outcome before retrying. This wrapper only starts fresh runs.

## 6. Change settings or hardware deliberately

| Change | Where | Effect |
|---|---|---|
| Iterations, epochs, time, VRAM | Your `experiments/*.json` | New demo schedule/budgets |
| Selected GPU | Optional `gpu` expectation and suitable `vram_gib` | New hardware run; checks the visible logical device |
| Provider/model | Your `llm/*.json` selected by `llm_config` | New model treatment and possibly new required keys |
| Task description | Copy of the whole task package selected by `composition` | New fingerprint; notebook demonstrates a controlled edit |
| Train/validation membership | Demo 4 creates a new task manifest and matching NPZ archives | New scientific split; preserve whole-star independence |
| Input length, metric, Health | Task declaration **and** runtime/tests | Qualify the changed task; not an arbitrary launcher override |

Set `gpu` to `null` (or omit it) to use the visible device without a model-name
expectation. An explicit string such as `H100` remains a required substring of
the detected name. On a multi-GPU host, select one visible device before launch,
for example `CUDA_VISIBLE_DEVICES=2`; the framework sees that physical card as
logical device 0. This tutorial does not launch distributed multi-GPU training.

Choose effective Trial/Formal VRAM budgets below that device's capacity. There
is no fixed 80 GiB schema ceiling; a larger device still needs working kernels
and resource accounting. Review host RAM, storage and time budgets separately.
A tiny kernel witness is a setup check, not proof that the generated model fits.
Native measurement, admission and runtime protection retain their own checks.

AMD/ROCm compatibility is experimental and untested. Required driver/process
accounting is not implemented for it, so this tutorial refuses that path before
allocation or provider calls. No ROCm installation profile is qualified here;
do not swap individual wheels or disable protection. A new dependency selection
requires a separately reviewed frozen environment. Hardware changes also change
how much search fits within a time budget; they do not reproduce the paper run.

## Execution boundary and the paper route

The script runs native fixed workflow under your normal user. There is no
external coding-agent shell or private evaluator service. Generated model
code runs in framework subprocesses with runtime controls; this is **not**
an OS sandbox against malicious code. Files readable by that user are not
made inaccessible by the notebook. Keep secrets and unrelated data out of the
run area. Do not claim process-level inference/validation-target isolation.

For the existing paper settings, use the original TESS supervisor on RTX 5090:

```bash
bash "$EXP_CHECKOUT/experiments/phyts_tess/main_fixed_workflow/launch.sh" \
  --siderius-checkout "$INFRA_CHECKOUT" \
  --data_dir "$TUTORIAL_HOME/data/tess-data" \
  --unit_dir "$TUTORIAL_HOME/new-paper-unit" \
  --run_name tess_paper_rerun_001 --arm no-prior
```

Review its preview before adding `--launch`. That route owns the immutable
six-hour clock, restart behavior and original settings; it does not read demo
JSON. The current pin includes fixes after some historical runs. Exact archived
replay needs that run's source pair, checkpoints and evidence, not just this
command. Support-code contracts and validation ownership are documented in
[implementation.md](implementation.md).
