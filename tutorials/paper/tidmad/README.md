# TIDMAD: one band, saved configurations, and file-range holdout

The [notebook](../notebooks/02_tidmad_tutorial.ipynb) teaches a complete sequence:
choose data, change settings, save your task/experiment, open the saved files,
then run the script that selects them. It uses **band 0–3** only. The notebook
prepares and explains; terminal scripts launch searches and final inference.

## Initialize your own project

Follow the [shared installation instructions](../README.md#1-install-in-the-two-exact-checkouts),
then run from the exact exp checkout:

```bash
export TUTORIAL_HOME=/absolute/path/to/my-tidmad-study
.venv/bin/python -B -m tutorials.paper.tidmad.project \
  --project "$TUTORIAL_HOME" --infra-checkout /absolute/path/to/SIDERIUS-tutorial
.venv/bin/jupyter lab --ServerApp.root_dir="$TUTORIAL_HOME"
```

The project directory must be new and outside both repositories. Open its
`notebooks/02_tidmad_tutorial.ipynb` with the exp environment's kernel.

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

Do not run both preparations. Both entrances yield the same `data_dir`: only
training/validation files 0000–0003 and `segment_anchors.json`. One band still
represents about 32 GB of uncompressed channel samples. No download occurs
when you run notebook cells.

## What files do my edits create?

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
10/20, while Formal `.1` declares the frozen 20/200 parent and uses all 20.
Changing the split is a new scientific protocol, not the frozen paper result.

Workflow validation influences the agent and training/model selection. Final
test happens only after selection: stop search, declare the selected native
model, seal its hashes, then run the separate test script. The notebook shows
all candidate-file fields and commands. Its report uses the selected task's
metric and scoreability contract, is diagnostic, and does not run the full
workflow Health assessment. Do not adapt the model to that final score.

## Keys, hardware and execution boundaries

Export keys into the launching terminal from a trusted external secret store
or mode-600 file. Never save values in notebooks, JSON, scripts or logs. The
launcher checks names/presence only and refuses missing keys. TIDMAD NoPrior
disables human advice and data analysis but retains literature review.

Supported devices are one NVIDIA RTX 5090 or H100 with working CUDA and memory
headroom. Another NVIDIA GPU needs GPU-check/CUDA/calibration qualification;
AMD and Intel are unsupported. Per-stage time allowances are not total campaign
or cost caps. The fixed workflow has no separate security sandbox: raw files
are locally readable and the holdout is procedural. Keep results and edited
inputs in your project; leave both source repositories unchanged.
