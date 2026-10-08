# Cancer genes: learn the workflow on one biological graph

This notebook takes one complete CPDB network from local data to a saved task,
editable experiment, three-iteration search and score plot. Start with the
[notebook](cancer_tutorial.ipynb) to see the file layout and controls, then follow
the setup below. The [recorded example](example/README.md) shows real CPDB data,
three measured scores and the exact source/data provenance. Your copied notebook
starts with cleared outputs and produces your own results.

Cancer is outside the paper's four experiments. This is a process demo, not the
eight-network NatureBench benchmark, a paper artifact or a clinical predictor.
The original Train/Validation/Test masks remain unchanged. Validation guides the
search; Test labels are not loaded or scored.

## 1. Set up the two matching repositories

Use Linux and a supported NVIDIA GPU for training. You can inspect data and
existing results on CPU, but CPU training is unsupported. Install the paired
sources in their own environments using the commands below. The separate
[shared LLM guide](../../shared/README.md) explains model routing and key setup.
For a fresh installation:

```bash
git clone https://github.com/yuema137/siderius-exp.git
cd siderius-exp
export EXP_CHECKOUT="$PWD"
git clone https://github.com/yuema137/SIDERIUS.git ../SIDERIUS
export SIDERIUS_CHECKOUT="$(cd ../SIDERIUS && pwd)"
git -C "$SIDERIUS_CHECKOUT" checkout "$(cat SIDERIUS_REVISION)"
uv sync --python 3.12 --group dev --group tutorial --frozen
(cd "$SIDERIUS_CHECKOUT" && uv sync --group dev --frozen)
```

The demo starts with **10 GiB Trial/Formal VRAM allowances**, not a measured
minimum. The physical GPU must be larger than the selected allowance, and current
occupied VRAM plus that allowance must fit the resolved capacity/quota. Other
NVIDIA models may work; they have not all been tested. AMD/ROCm is experimental
and currently lacks required tutorial accounting; Intel GPU is unsupported.
Do not disable protection to make a check pass.

CPDB occupies **1,500,816,975 bytes (about 1.50 GB)**. Four CPU loader previews
peaked near 980 MiB host RAM on one machine; this is not a training RAM minimum
or upper bound. Generated graph models can require more RAM and VRAM. Leave
additional disk space for environments, checkpoints and results. A smaller
label fraction does not make this graph smaller. See the
[hardware guide](../../shared/hardware/README.md) before paid execution.

## 2. Reuse or obtain the single CPDB file

The data directory must contain `cpdb/data.h5`. If the dataset already exists
on your machine or shared server, point directly to it; do not download another
copy. The tutorial never modifies it.

```bash
export CANCER_DATA="/absolute/path/NatureBench/tasks/s41551-024-01312-5/problem/data"
```

If absent, download **only CPDB** from the pinned
[FrontisAI/NatureBench source](https://huggingface.co/datasets/FrontisAI/NatureBench/tree/9e6a69f10865dd56f4991b49d1c974e2006b6b18/tasks/s41551-024-01312-5/problem/data/cpdb):

```bash
mkdir -p "$CANCER_DATA/cpdb"
curl --fail --location --output "$CANCER_DATA/cpdb/data.h5" \
  'https://huggingface.co/datasets/FrontisAI/NatureBench/resolve/9e6a69f10865dd56f4991b49d1c974e2006b6b18/tasks/s41551-024-01312-5/problem/data/cpdb/data.h5?download=true'
```

Use that command only when the file is missing. The copied task's
`declared/tutorial_source_files.json` owns its exact size and SHA-256. Preview
checks size and mask structure; launch verifies full SHA-256. No index-building
or second prepared-data directory is needed.

## 3. Create your own project

Keep it separate from both repositories and the raw data. This command copies
small task/configuration/notebook files, not the dataset:

```bash
export TUTORIAL_HOME="/absolute/path/my-cancer-demo"
cd "$EXP_CHECKOUT"
.venv/bin/python -m tutorials.supplementary.cancer.project \
  --project "$TUTORIAL_HOME" --infra-checkout "$SIDERIUS_CHECKOUT" \
  --data-dir "$CANCER_DATA"
```

Your project contains:

| File or directory | What it owns |
|---|---|
| `tasks/cancer/compositions/cpdb_tutorial.yaml` | Complete CPDB, original validation mask, metric and loss bindings |
| `tasks/cancer/declared/` | Task description, tensor contract and source identity |
| `tasks/cancer/plugins/` | Graph loader, reference model, masked BCE and metrics |
| `experiments/cancer-demo.json` | Iterations, label fractions, time/VRAM allowances and output location |
| `experiments/workflow.json` | Native workflow choices, including operator-controlled Formal fractions |
| `llm/agents.json` | All-Luna test routing; key names, never key values |
| `scripts/run-cancer.sh` | Reads the saved JSON and launches the native workflow |
| `notebooks/cancer_tutorial.ipynb` | Your editable explanation, previews and save-as controls |
| `runs/cancer_demo_001/` | Native results after launch |
| `plots/` | Score PNG, SVG and CSV |

Edit these copied files. Never edit tracked repository templates to run a
personal experiment. There is no active human-advice file, Data Analysis or
literature-review step in this short treatment.

## 4. Understand the knobs before spending API credit

CPDB is **one complete graph per sample**, with 13,627 nodes, 64 node features
and 504,378 non-self directed edges. The packed model input is `[518005, 68]`;
batch size must remain **1**. Every node's features and graph connections are
visible. The task masks determine which labels contribute to training and scoring.

The initial experiment uses 3 iterations, 2 tuning rounds, 1 epoch, all original
Train/Validation labels, 2/5 minute Trial/Formal training allowances and 10 GiB
VRAM allowances. Change these in the notebook and save a fresh named variant.

- `trial_train_label_fraction` and `formal_train_label_fraction` select active
  labels from the original Train mask. At 0.25, 504 of 2,013 labels are active.
- `trial_eval_label_fraction` and `formal_eval_label_fraction` select labels
  from the original Validation mask. At 0.25, 56 of 224 labels are selected.
- **Neither reduces graph size or graph computation.** A tiny validation subset
  can miss one class and become unscoreable. Defaults use all validation labels.
- `iterations`, `rounds`, `epochs`, `trial_minutes`, `formal_minutes` and VRAM
  fields control the experiment, not the scientific split.

Counts/class counts displayed by the notebook use seed 42 as an illustration;
they do not certify every later attempt's class support. No test-set resplitting
or hidden final-test scorer is implemented here. The native `regressor` option
refers to the structured float output; scientifically this is binary node
classification with task-owned masked binary cross-entropy.

## 5. Check hardware, keys and the exact saved script

Run this **from the exp checkout**, after saving the experiment you intend to
launch. The following pair selects the initial demo:

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -m tutorials.shared.hardware \
  --experiment "$TUTORIAL_HOME/experiments/cancer-demo.json"
bash "$TUTORIAL_HOME/scripts/run-cancer.sh"
```

For a saved variant, change **both paths** to the pair printed by the notebook.
For example, `cancer-four-001` uses
`experiments/cancer-four-001.json` for the hardware check and
`scripts/run-cancer-four-001.sh` for the preview. Each script is bound to its
matching JSON; `run-cancer.sh` continues to select the initial demo.

The first command checks hardware without keys or training; it runs a tiny GPU
kernel and reports current capacity, occupancy, quota and host RAM/disk
observations. It reserves no GPU memory and cannot prove a generated model fits.
The second command is an offline launch preview, which does not call the API or
GPU. Review the saved settings and exact native command it prints.

Before actual launch, export your own `OPENAI_API_KEY` from a trusted external
secret file or secret manager **in the terminal that starts Jupyter/the script**.
Do not paste keys into notebooks, JSON or Git. Missing credentials or prerequisites
produce errors. The [shared LLM guide](../../shared/README.md) distinguishes cheap
Luna process testing from research and custom configurations. Time allowances
and notebook timeout are not API billing limits.

## 6. Open the copied notebook, run and find results

```bash
"$EXP_CHECKOUT/.venv/bin/python" -m ipykernel install \
  --prefix "$TUTORIAL_HOME/.jupyter" --name siderius-cancer-tutorial \
  --display-name "SIDERIUS Cancer tutorial"
export JUPYTER_PATH="$TUTORIAL_HOME/.jupyter/share/jupyter${JUPYTER_PATH:+:$JUPYTER_PATH}"
export IPYTHONDIR="$TUTORIAL_HOME/.ipython"
export MPLCONFIGDIR="$TUTORIAL_HOME/.matplotlib"
export JUPYTER_RUNTIME_DIR="$TUTORIAL_HOME/.jupyter/runtime"
cd "$TUTORIAL_HOME"
"$EXP_CHECKOUT/.venv/bin/jupyter" lab --ServerApp.root_dir="$TUTORIAL_HOME"
```

Open `notebooks/cancer_tutorial.ipynb` and select **SIDERIUS Cancer tutorial**.
The notebook checks the exp interpreter and `TUTORIAL_HOME`. Restart Jupyter
from this terminal after changing exported variables. Sections 1–4 show data,
explain edits and review saved files.
**Run All reaches section 5 and starts API/GPU work when `RUN_QUICK_DEMO=True`.**
Set it to `False` for inspection only. The notebook delegates execution to the
saved script; the direct initial command is:

```bash
bash "$TUTORIAL_HOME/scripts/run-cancer.sh" --launch
```

A named variant has its own `run-<name>.sh`, saved JSON and workspace; the notebook
prints all three. Original inputs/results are not overwritten. An unchanged
completed notebook run reuses its saved result; a changed or interrupted run
requires a fresh variant.

The last cell plots native Formal `mean_auprc` scores and saves PNG/SVG/CSV under
`plots/`. For one network, that score is CPDB validation average precision. It is
not an eight-network comparison or final blind Test score. Hollow points mark
invalid/rejected scored attempts; missing scores are not invented zeros. No
Health checks are declared: successful execution does not mean Health PASS.

The run directory contains native manifests and per-iteration records. Notebook
console log and completion receipt are siblings named `.console.log` and
`.notebook-run.json`; a direct script prints to its terminal. You can select an
older saved JSON in the plot cell without launching it again.

Technical ownership and validation boundaries: [implementation reference](implementation.md).
