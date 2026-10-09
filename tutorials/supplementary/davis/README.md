# DAVIS: predict four future video frames

This notebook teaches the complete path from local video data to your own saved
task and experiment, a three-iteration run, and a score plot. Start with the
[notebook](davis_tutorial.ipynb) to see the steps, then use the setup below.
The [recorded three-iteration demo](example/README.md) shows real input/target
frames and a score plot. Its first candidate failed the unchanged Health check;
the next two passed. All outcomes remain visible.

DAVIS is outside the paper's four experiments. This is a small workflow demo,
not a paper artifact or a competitive video-prediction benchmark. The original
sequence split stays unchanged: 60 Train, 15 Validation and 15 Final sequences.
Validation guides the agent. Final sequences are not used in this tutorial.

## 1. Install the matching repositories and check requirements

Use Linux and an NVIDIA GPU with working CUDA and memory accounting for
training. CPU data previews are supported, but CPU/Intel training is not.
AMD/ROCm is experimental and currently lacks the required tutorial accounting.
Other NVIDIA models can use the same checks; they have not all been tested.

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

The initial **10 GiB Trial/Formal VRAM allowance is a configurable budget**, not
a measured minimum or proof that every generated model fits. The GPU must have
more physical capacity than the allowance, and current occupied memory plus
the allowance must fit capacity and any deployment quota. Do not disable checks
or merely reduce a cap to make an oversized model appear acceptable.

Keep the **832,766,765-byte archive (about 0.833 GB)** plus extracted frames,
environments, checkpoints and results. Selected clips decode lazily; batch size,
model and loading affect host RAM use. No universal RAM minimum or maximum has
been qualified. The [hardware guide](../../shared/hardware/README.md) explains
how to check GPU readiness and inspect available RAM/disk before spending API
credit. Smaller clip fractions reduce work, not the size of each video tensor.

## 2. Download the archive and extract the frames

Use the task-owned helper to fetch and verify the official archive, extract it
and check the sequence layout:

```bash
export DAVIS_DATA="/absolute/path/data/DAVIS_2017"
cd "$EXP_CHECKOUT"
.venv/bin/python -m tasks.davis_future_prediction.tools.fetch_davis \
  --dest "$DAVIS_DATA" --extract --check-layout
```

Success prints `[layout] ... sequences present`. Keep both
`DAVIS-2017-trainval-480p.zip` and the extracted `DAVIS/JPEGImages/480p/` tree
under `DAVIS_DATA`. Pass this outer directory to `--data-dir` in the next step;
do not pass `JPEGImages` itself. It becomes `data_dir` in `experiments/davis-demo.json`.
The [shared directory guide](../../README.md#source-project-data-and-run-directories)
explains how inputs differ from the project and run outputs.

The helper reuses and verifies a present archive. Keep data outside
both repositories. See the [data guide](../../../tasks/davis_future_prediction/data/README.md)
for the exact directory layout, original split and data terms. The tutorial
never regenerates manifests or copies video files into your project.

Preview verifies frozen manifest identity and required frame presence. Launch
also verifies the original archive and ten fixed decoded windows. This checks
those named windows, not every extracted image. Verifying the archive alone
does not establish that all extracted images are unchanged.

## 3. Create an external project

```bash
export TUTORIAL_HOME="/absolute/path/my-davis-demo"
cd "$EXP_CHECKOUT"
.venv/bin/python -m tutorials.supplementary.davis.project \
  --project "$TUTORIAL_HOME" --infra-checkout "$SIDERIUS_CHECKOUT" \
  --data-dir "$DAVIS_DATA"
```

Keep this folder separate from the repositories and raw data. Edit only its
copied files; source templates and old results stay untouched.

| File or directory in your project | What it owns |
|---|---|
| `tasks/davis/compositions/bounded_qualification.yaml` | Task bindings, original Train/Validation manifest selection, loss and metric |
| `tasks/davis/data/manifests/` | Original sequence/clip identities and decode probes |
| `tasks/davis/declared/` | Task description, tensor contract, metrics and Health policy |
| `tasks/davis/runtime/`, `tasks/davis/plugins/` | Decoder, loss, reference model and scoring |
| `experiments/davis-demo.json` | Your iterations, fractions, time/VRAM allowances and workspace |
| `experiments/workflow.json` | Native workflow choices, including operator-controlled Formal scope |
| `llm/agents.json` | All-Luna test routes; key names, never key values |
| `scripts/run-davis.sh` | Saved execution entry point reading that JSON |
| `notebooks/davis_tutorial.ipynb` | Explanation, previews, edits and saved-script invocation |
| `runs/davis_demo_001/` | Native results created by launch |
| `plots/` | PNG, SVG and CSV generated from recorded results |

There is no active advice file, Data Analysis or literature-review step here.
The [shared LLM guide](../../shared/README.md) distinguishes cheap process-test
routing, paper research configurations and user-defined model choices.

## 4. Know what the controls change

One sample has eight context frames `[3,8,128,224]` and four target frames
`[3,4,128,224]`. The notebook displays all twelve real frames. The bounded task
uses the first window of each sequence, with the original 60/15/15 split.

Defaults are 3 iterations, 2 tuning rounds, 1 epoch, 2/5 minute Trial/Formal
training allowances and 10 GiB VRAM allowances. The notebook can save a fresh
named variant, for example four iterations with a larger Formal training scope:

```python
SAVE_VARIANT = True
VARIANT_NAME = "davis-four-001"
CHANGES = {"iterations": 4, "formal_train_fraction": 0.75}
```

That writes `experiments/davis-four-001.json`,
`scripts/run-davis-four-001.sh` and a new `runs/davis-four-001/` location.
The notebook prints their absolute paths and selects the new pair for the
following cells. For a **later Run All or reopened notebook**, also set
`SELECTED_EXPERIMENT = "davis-four-001"` in section 1 and `SAVE_VARIANT=False` in
section 3. Section 1 otherwise selects the starting `davis-demo` again; leaving
save enabled would try to recreate files that already exist.

- `trial_train_fraction=0.25` selects 15 of 60 Train clips.
- `formal_train_fraction=0.5` selects 30 of 60 Train clips; 0.75 selects 45.
- `trial_eval_fraction` and `formal_eval_fraction` default to 1: all 15
  Validation clips. Fractions range from 0.01 to 1, using the task's
  `max(1, round(fraction × count))` rule.
- `iterations`, `rounds`, `epochs`, phase time allowances and VRAM fields control
  execution. Phase-specific VRAM overrides can replace `vram_gib`.

Fractions select whole clips within the fixed role; they do not change frame
size or the 8→4 prediction problem. Epoch `train_portion` stays 1: this task
refuses fractional epoch sampling. Formal scope is explicitly operator-controlled.
After editing the copied task description, restart the notebook kernel before
reviewing it again; cached configuration is refused rather than treated as fresh.
Task changes such as new splits, decoder, loss or Health policy require a
separate scientific experiment; the tutorial does not silently rewrite them.

## 5. Review your saved setup, keys and exact command

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -m tutorials.shared.hardware \
  --experiment "$TUTORIAL_HOME/experiments/davis-demo.json"
bash "$TUTORIAL_HOME/scripts/run-davis.sh"
```

Use your variant's JSON/script paths if you saved one. The first command needs
no API key and starts no training; it queries GPU memory and runs a tiny kernel.
It reports capacity, occupancy, quota and host RAM/disk observations. A passing
check is a snapshot, not a reservation or model-fit guarantee. The second
command is an offline preview, with no API/GPU effects. Inspect its saved values,
selected task, original manifests, workflow, LLM routes and native command.

Before launching, export your own `OPENAI_API_KEY` from a trusted external
secret file or secret manager in the terminal that starts Jupyter/the script.
Never paste keys into notebooks, JSON or Git. Missing prerequisites produce
errors. Time allowances and notebook timeout are not whole-run billing limits.

## 6. Open your notebook and run the saved script

```bash
"$EXP_CHECKOUT/.venv/bin/python" -m ipykernel install \
  --prefix "$TUTORIAL_HOME/.jupyter" --name siderius-davis-tutorial \
  --display-name "SIDERIUS DAVIS tutorial"
export JUPYTER_PATH="$TUTORIAL_HOME/.jupyter/share/jupyter${JUPYTER_PATH:+:$JUPYTER_PATH}"
export IPYTHONDIR="$TUTORIAL_HOME/.ipython"
export MPLCONFIGDIR="$TUTORIAL_HOME/.matplotlib"
export JUPYTER_RUNTIME_DIR="$TUTORIAL_HOME/.jupyter/runtime"
cd "$TUTORIAL_HOME"
"$EXP_CHECKOUT/.venv/bin/jupyter" lab --ServerApp.root_dir="$TUTORIAL_HOME"
```

Open `notebooks/davis_tutorial.ipynb` with **SIDERIUS DAVIS tutorial**. Sections
1–4 inspect data, explain controls and review saved files. **Run All reaches
section 5 and starts API/GPU work when `RUN_QUICK_DEMO=True`.** Set it to `False`
for inspection only. The direct command for the starting experiment is:

```bash
bash "$TUTORIAL_HOME/scripts/run-davis.sh" --launch
```

An unchanged completed notebook run reuses its result. For changed inputs or an
interrupted run, retain old records and save a fresh named variant. The notebook
owns no alternate trainer; it invokes the exact saved script.

## 7. Find and interpret the result

The last cell plots recorded Formal **MSE: lower is better**. Exact-L1 is the
training loss; MSE is the primary evaluation score, with PSNR and MAE recorded
as secondary metrics. The original task Health gate rejects near-constant
predictions by dispersion. Successful training alone does not mean Health PASS.
Invalid/rejected scored points are hollow; no score is replaced with a fake zero.
A poor or invalid result still demonstrates the workflow.

Inspect native manifests and records under `runs/<run_name>/`. The notebook log
and completion receipt are siblings named `.console.log` and `.notebook-run.json`;
a direct script prints to its terminal. Plots and source CSV go under
`plots/<experiment-name>/`. Choose an older saved JSON in the plot cell to view
its results without running again. Final clips remain unused; these are search
validation scores, not final-test performance.

Technical ownership and validation boundaries: [implementation reference](implementation.md).
