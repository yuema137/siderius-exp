# TIDMAD: one band, saved configurations, and file-range holdout

The [notebook](../notebooks/02_tidmad_tutorial.ipynb) teaches a complete sequence:
choose data, change settings, save your task/experiment, open the saved files,
then run the script that selects them. It uses **band 0–3** only. The notebook
prepares and explains; its Run All quick-demo cell invokes a saved search
script and plots score versus iteration. Set `RUN_QUICK_DEMO=False` to skip paid
execution; Quick demo A still saves inputs in your project. Final inference
belongs to a separate optional example, described below.

## Initialize your own project

Follow the [shared installation instructions](../README.md#1-install-in-the-two-exact-checkouts),
then run from the exact exp checkout:

```bash
export TUTORIAL_HOME=/absolute/path/to/my-tidmad-study
export PYTHONDONTWRITEBYTECODE=1
cd "$EXP_CHECKOUT"
.venv/bin/python -B -m tutorials.paper.tidmad.project \
  --project "$TUTORIAL_HOME" --infra-checkout "$INFRA_CHECKOUT"
```

The project directory must be new and outside both repositories. Prepare data
and export keys below before starting Jupyter.

## Choose existing data OR a download

**Shared 5090 machine:** reuse the existing large files, without copying or
re-downloading them:

```bash
.venv/bin/python -B -m tutorials.paper.data_entry --task tidmad \
  --project "$TUTORIAL_HOME" --source /home/klz/Data/TIDMAD
```

This verifies the eight source hashes and creates only symbolic links in
`data/band-0-3/`. The small scoring anchor is local. Keep the shared source
paths available; tutorial execution reads them and writes outputs elsewhere.

**Your own machine:** use the official [TIDMAD downloader](https://github.com/jessicafry/TIDMAD),
kept outside both source checkouts:

```bash
python /absolute/path/to/TIDMAD/download_data.py \
  --output_dir "$TUTORIAL_HOME/data/band-0-3" \
  --train_files 4 --validation_files 4 --science_files 0
```

Do not run both preparations. Both options yield the same `data_dir`: only
training/validation files 0000–0003 and `segment_anchors.json`. One band still
represents about 32 GB of uncompressed channel samples. No download occurs
when you run notebook cells.

## Export keys, select the kernel, then run the notebook

The shipped routing needs **`OPENAI_API_KEY`**. In this same terminal:

```bash
read -r -s -p "OpenAI API key: " OPENAI_API_KEY
echo
export OPENAI_API_KEY
```

This keeps the value out of shell history and notebook cells. For repeat use,
see the [shared key instructions](../README.md#2-configure-keys-without-storing-them-in-a-notebook).
TIDMAD keeps literature review enabled; changing provider routing can change
which key names are required. The launcher checks the selected routing.

Register the exp checkout's kernel and start Jupyter only after data and keys
are ready:

```bash
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

Open `notebooks/02_tidmad_tutorial.ipynb`, select **SIDERIUS exp tutorial**, then
use **Run All**. Quick A saves/checks inputs, Quick B runs the saved script,
and Quick C plots the records. You can stop at the plot; no extra terminal
launch is needed. With the default `DEMO_NAME="quick-demo-001"`, your files are:

```text
YOUR_PROJECT/
├── tasks/tidmad-quick-demo-001/compositions/file_holdout.yaml
├── experiments/tidmad_quick-demo-001.json
├── scripts/run-tidmad_quick-demo-001.sh
├── runs/tidmad_quick-demo-001/
└── plots/tidmad_quick-demo-001/score-versus-iteration.png
```

The notebook prints absolute paths and lets you reopen the saved JSON. The
quick demo is complete even if its scores are invalid; those points are hollow.
A three-iteration run took about 35 minutes on our RTX 5090, including LLM work.

## Optional advanced examples: what files do my edits create?

These examples save **different experiments** from the quick demo above. Use
them to learn a particular change; they do not automatically reuse its results.

A task is a directory with a composition YAML entry. An experiment is one JSON
file pointing to that entry. A script points to the JSON through `EXPERIMENT`.
After section 5's `SAVE_EXAMPLES=True`, the file-split example is:

```text
YOUR_PROJECT/
├── tasks/tidmad/compositions/file_holdout.yaml   train/validation/test file lists
├── experiments/tidmad-file-split.json            task path, fractions and budgets
├── llm/agents.json                              model/provider routing, NO keys
├── advice/README.txt                            advice is inactive in NoPrior
├── scripts/run-tidmad-file-split.sh              runs that experiment
├── scripts/test-tidmad-file-split.sh             post-selection final test
├── data/band-0-3/                               source inputs
├── runs/tidmad_file_split_001/                   future search output
└── final-test/                                 selected model and test output
```

Open these saved files in JupyterLab's file browser or use the notebook's
read-back cells. Changing a Python variable alone does not change a file.
The initial `run-tidmad.sh` continues to select `tidmad-experiment.json`; it
does not automatically switch to your new demo. For the new split, run:

```bash
bash "$TUTORIAL_HOME/scripts/run-tidmad-file-split.sh"          # preview
bash "$TUTORIAL_HOME/scripts/run-tidmad-file-split.sh" --launch # API/GPU work
```

The notebook provides equivalent experiment/script pairs for longer search,
smaller Trial data and changed time/VRAM budgets. Launch always reads saved files.

## Understand the split and the proportions

The new task uses training indices `[0,1]`, workflow-validation index `[2]`, and
final-test index `[3]`. It reads `abra_training_0000/0001.h5` for training and
`abra_validation_0002/0003.h5` for validation/test respectively. Edit the three
lists to define another disjoint partition of 0–3. All original segments in
an assigned file remain eligible; no per-second FFT labeling or weak-signal
filter is applied. This is file-index/frequency-range holdout, not proof of
exact spectral non-overlap.

In the new task, Trial `.25` takes 50/200 segments per training file; Formal
`.5` takes 100/200. Evaluation fractions apply only to validation file 2.
Final-test file 3 never enters workflow scopes. In contrast, the original
paper-pool example fixes 20 training segments per file: Trial `.5` means
10/20. Keep `formal_train_fraction=0.1` for that frozen task: it selects the
original 20 of 200 segments, and Formal uses all 20.
Changing the split is a new scientific protocol, not the frozen paper result.

The final-test instructions below belong to `tidmad-file-split`, not the quick
demo. To follow them, save and run that optional example in notebook sections
5–6 first. They do not automatically select a model from the quick-demo run.

Workflow validation influences the agent and training/model selection. Final
test happens only after selection: stop search, declare the selected native
model, seal its hashes, then run the separate test script. The notebook shows
how to select a saved successful attempt and generate `final-test/candidate.json`
from its recorded artifact paths. Search scripts retain the training checkpoint
for this step. Its report uses the selected task's
metric and scoreability contract, is diagnostic, and does not run the full
workflow Health assessment. Do not adapt the model to that final score. If no attempt succeeds, stop before
final testing and inspect the validation failure records. This does not prevent completion of the workflow demo or plotting its results.

## Keys, hardware and execution boundaries

Export keys into the launching terminal from a trusted external secret store
or mode-600 file. Never save values in notebooks, JSON, scripts or logs. The
launcher checks names/presence only and refuses missing keys. TIDMAD NoPrior
disables human advice and data analysis but retains literature review.

Select one visible GPU with working kernels and required accounting, and keep
resource budgets below its capacity. Names are not restricted to specific NVIDIA
models; an explicit `gpu` value remains a name expectation. Follow the
[shared hardware instructions](../README.md#6-change-settings-or-hardware-deliberately),
including the pending paired-pin qualification. AMD/ROCm is experimental and
untested; missing driver accounting currently prevents this tutorial route.
Intel GPU training is unsupported. Per-stage time allowances are not total campaign
or cost caps. The fixed workflow has no separate security sandbox: raw files
are locally readable and the holdout is procedural. Keep results and edited
inputs in your project; leave both source repositories unchanged.
