# Paper tutorials: configure a scientific task and launch your own run

Use these tutorials to learn **which files define a task, which parameters define
an experiment, and which terminal command runs what you saved**. You work in your
own project directory. The notebook explains and saves configurations; a separate
shell script launches the fixed workflow and writes results into that project.

## Choose a tutorial

| Tutorial | Scientific question | What you can change | Start here |
|---|---|---|---|
| **TESS** | Predict a star's rotation frequency from its brightness measurements over time | Iterations, epochs, Trial/Formal fractions, time/VRAM budgets, and a new whole-star train/validation split | **[Open the TESS notebook](notebooks/01_tess_tutorial.ipynb)**; follow setup below before executing your own copy |
| **TIDMAD, band 0–3** | Recover an injected waveform from noisy detector measurements | The same budgets/fractions, plus file-index training/validation/final-test groups | **[TIDMAD setup and walkthrough](tidmad/README.md)** · **[Open the TIDMAD notebook](notebooks/02_tidmad_tutorial.ipynb)** |
| LIGO | Gravitational-wave task | No runnable tutorial yet | [Existing task package](../../tasks/phyts_ligo/README.md) |
| Project 8 | Paper time/frequency four-channel task | No runnable tutorial yet | [Existing task documentation](../../tasks/phyts_project8/DUAL_REPRESENTATION.md) |

For the underlying TESS task and data contract, see the
[TESS task package](../../tasks/phyts_tess/README.md). The tutorial downloads its
pinned [PhyTS TESS data](https://huggingface.co/datasets/PhyTS-team/PhyTS-bench/tree/9f203f4c338645a1e4b2c9dc7d6f820269ca5114/TESS/split),
or reuses the shared machine's existing files.

## What these tutorials can—and cannot—do

You can use them to prepare data, configure model/provider routing without saving
keys, save a task/experiment variant, check its actual files and parameters, run
it on a supported GPU, and inspect the resulting records. Each notebook has a
**Before you run** checklist that prints the exact preview and launch commands
for the one saved experiment you select.

These are **learning and execution demos**, not a claim of complete paper
reproduction. Only TESS and one-band TIDMAD currently have notebooks. Fresh LLM
searches may produce different models and scores. The demos do not reproduce
the paper's coding-agent/orchestration comparisons or retrospective reviews.
Archived-checkpoint replay and the original campaign launchers are separate
routes. Changing a split defines a new scientific protocol.

The real TESS smoke run produced diagnostic scores. The tiny one-epoch TIDMAD
smoke run completed training/inference but all three attempts collapsed; it
produced no valid model for final testing. The separate TIDMAD final-test path
therefore does not yet have a successful real-run qualification. Do not treat
small fractions or a completed command as proof of model quality.

## What you will see after Run All

With the external project, data and exported keys ready, the notebook saves a
three-iteration experiment, displays its files/parameters, invokes its shell
script, and draws **score versus iteration** from actual run records. Filled
markers mean Health PASS; hollow markers mean Health FAIL/failed attempts.
The plot follows the paper: dashed Formal results, a solid current-best line,
and stars for new bests with Health PASS. Negative scores use boundary triangles;
missing scores stay in the CSV. The current-best line can include invalid points. CSV, PNG and SVG outputs are saved under your project's `plots/`.

Before a new run, the notebook and script check the checkout Python environments,
required input files, exported API key names and NVIDIA GPU access. Errors list
missing items and repair steps. The native preflight also checks source pins,
data integrity and CUDA allocation. Export keys **before starting Jupyter**;
restart its server from that terminal after changing the environment. Key presence
does not verify provider authentication or credit.

Re-running an unchanged completed demo redraws results without another API call.
To plot a different run, change `PLOT_WORKSPACE` and execute only the plotting
cell. To launch changed settings, choose a new `DEMO_NAME`. Three iterations can
still take many minutes because each includes LLM work and native checks; small
budgets do not guarantee a valid model. Independent final testing is a separate,
manual model-selection step, not part of the quick-demo validation plot.

## Before you start

- Linux, Python 3.12, `git`, `uv`, and one supported NVIDIA RTX 5090 or H100.
  AMD/Intel GPUs and CPU training are unsupported; H100 has no local real-run witness.
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
through sections 2–4, then open your copied notebook and its **Before you run**
checklist. For TIDMAD, continue with the [TIDMAD guide](tidmad/README.md) after
section 1. The commands in the remaining sections of this page are TESS examples.

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

Use Linux and Python 3.12. The teaching launcher accepts one RTX 5090 or H100
with a working NVIDIA driver and the locked CUDA PyTorch installation. AMD,
Intel GPU and CPU execution are not supported. The TESS paper deployment used
RTX 5090 with an 8 GiB model budget; H100 is an additional tutorial route.

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

The historical model ID is retained. If your account cannot use it, edit
your project's `llm/agents.json` and select an available model there, as shown in the notebook. That is a new model treatment, not an exact
paper rerun. Key presence does not prove provider access; only a request can.

## 3. Create your own project, then open its notebook

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
cd "$TUTORIAL_HOME"
"$EXP_CHECKOUT/.venv/bin/jupyter" lab --ServerApp.root_dir="$TUTORIAL_HOME"
```

Open `notebooks/01_tess_tutorial.ipynb` and select **SIDERIUS exp tutorial**.
The notebook reads `project.json` to find installed code, then inspects your
copied task and experiment. **After preparing data in section 4**, Run All
saves and executes a three-iteration quick demo, then plots its actual Formal
scores and Health markers. This uses paid APIs and GPU time. Set
`RUN_QUICK_DEMO=False` to skip execution. Advanced opt-in exercises save separate
experiment/scripts and optionally create a re-split task/data pair in your
project, never in either repository.

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

On the shared 5090 machine, reuse the existing source files instead of downloading:

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -B -m tutorials.paper.data_entry --task tess \
  --project "$TUTORIAL_HOME" --source /home/klz/Data/TESS/split
```

This verifies the pinned Parquet files and writes only the two required NPZ run
inputs (about 18 MB). Raw Parquet is neither downloaded nor copied. If a verified
NPZ directory already exists, set your saved experiment's `data_dir` to that
absolute path and reuse it without staging again. Do not expose the test split.

On another machine, use the download entrance below instead. Run from exp:

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

## 5. Preview, launch, inspect

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

The notebook starts by explaining iterations, epochs, Trial and Formal in
plain language, then gives four demos. Each demo starts from the same original
experiment, so its effect can be understood independently.

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
Formal training and validation fractions are separate operator-owned controls.

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
both staged populations, hashes, GPU name/capacity and an actual CUDA allocation
in infra's environment. It refuses root execution.

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
| RTX 5090 ↔ H100 | `gpu` and suitable `vram_gib` | New hardware run; launcher checks physical card |
| Provider/model | Your `llm/*.json` selected by `llm_config` | New model treatment and possibly new required keys |
| Task description | Copy of the whole task package selected by `composition` | New fingerprint; notebook demonstrates a controlled edit |
| Train/validation membership | Demo 4 creates a new task manifest and matching NPZ archives | New scientific split; preserve whole-star independence |
| Input length, metric, Health | Task declaration **and** runtime/tests | Qualify the changed task; not an arbitrary launcher override |

For **another NVIDIA GPU**, first verify that locked PyTorch can allocate a
CUDA tensor on it. Choose a VRAM budget below physical capacity; review RAM,
disk and time budgets. The current installed launcher accepts RTX 5090/H100 only; another card needs
a separately qualified launcher release from the maintainers. Do not edit the
installed repository as a tutorial step. Unknown GPUs are refused until an
updated release supports them. Do not
remove CUDA or capacity checks. `CUDA_VISIBLE_DEVICES` does not turn the
one-physical-GPU check into multi-GPU support.

A new card may need another driver/PyTorch build. If the frozen environment
cannot run it, create a separately tested dependency revision. AMD/Intel
adaptation is out of scope. Supporting a card here does not change the paper
supervisor. Different GPUs complete different amounts of search in the same
wall time, so changing hardware is not an identical experiment.

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
