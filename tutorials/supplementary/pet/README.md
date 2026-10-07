# Pet image-classification demo

Learn how a task package turns JPEG images into a classification problem, change
an experiment, run three research iterations, and plot the measured scores.
This supplementary example uses Oxford-IIIT Pet; it is **not a paper artifact,
benchmark, or promise of Health PASS**.

Open the [notebook](pet_tutorial.ipynb) to see the complete sequence. Your notebook
edits files in a new external project; your saved shell script launches SIDERIUS.
The repositories remain unchanged.

## 1. Install the exact environments

Clone the public repositories into separate directories. Replace the example
paths with your own absolute paths throughout these instructions.

```bash
git clone https://github.com/yuema137/siderius-exp.git /absolute/path/siderius-exp
git clone https://github.com/yuema137/SIDERIUS.git /absolute/path/SIDERIUS
cd /absolute/path/siderius-exp
uv sync --group dev --group tutorial --frozen
git -C /absolute/path/SIDERIUS checkout "$(cat SIDERIUS_REVISION)"
cd /absolute/path/SIDERIUS
uv sync --group dev --frozen
```

Each checkout uses its own `.venv`. Pet explicitly selects the built-in
`native-timing-v1` planner. Preflight compares the planner identities resolved in
both environments and rejects missing or mismatched providers. Unlike the four
historical paper demos, Pet does not select a legacy planner plugin.

An NVIDIA RTX 5090 or H100 with working CUDA is supported by this launcher.
Run `nvidia-smi` first. For another NVIDIA GPU, save the previewed native command as a new script in
your external project, install PyTorch/CUDA for that device, and explicitly set
`--trial_vram_budget_gb` / `--formal_vram_budget_gb` below its physical VRAM.
Qualify that separate launch adapter on the device before relying on it; the
provided notebook launcher continues to refuse unsupported GPU names. Keep the
source repositories unchanged. A device-name change alone is not a validated port. AMD and Intel GPUs are unsupported.

## 2. Reuse images, or download once

If the dataset is already available, pass its **images directory**, containing
files such as `Abyssinian_100.jpg`, directly to project initialization. On the
shared 5090 host, the operator-provided location is
`/home/klz/Data/OXFORD_IIIT_PET/images`; this is an example deployment, not a default.
No JPEGs are copied or downloaded by initialization.

For another machine, the repository provides an explicit acquisition tool:

```bash
cd /absolute/path/siderius-exp
.venv/bin/python -m tasks.oxford_iiit_pet.tools.fetch_oxford_iiit_pet \
  --dest /absolute/path/data/OXFORD_IIIT_PET --extract
```

This verifies pinned archives. Do not download another copy if you already have
the images. The demo checks all declared image filenames and decodes search
images before launching; it never uses final-set pixels for search.

## 3. Initialize your project and export keys

```bash
cd /absolute/path/siderius-exp
.venv/bin/python -m tutorials.supplementary.pet.project \
  --project /absolute/path/my-pet-project \
  --infra-checkout /absolute/path/SIDERIUS \
  --images /absolute/path/data/OXFORD_IIIT_PET/images
```

Choose a new project outside both repositories and the dataset. Initialization
refuses an existing destination. It creates:

| File or directory | What you inspect or change |
|---|---|
| `tasks/pet/compositions/bounded_qualification.yaml` | Task components and train/validation CSV paths |
| `tasks/pet/data/manifests/` | Image IDs, class labels and split membership |
| `tasks/pet/declared/` | Model tensor contract, metrics and Health rules |
| `llm/agents.json` | Provider, model, reasoning effort and planner strategy; no keys |
| `experiments/pet-demo.json` | Iterations, epochs, fractions, time/VRAM and all absolute paths |
| `experiments/workflow.json` | Fixed workflow flags; experiment JSON owns the exposed knobs |
| `scripts/run-pet.sh` | Saved executable entrypoint, bound to that experiment JSON |
| `data/images.json` | Initial image-location receipt; `data_dir` in the experiment is authoritative |
| `runs/` | Fresh native workspaces, console log and completion receipts |
| `plots/` | Your exported PNG, SVG and CSV |

Export `OPENAI_API_KEY` from a trusted external secret source in the terminal
that starts Jupyter or the script. For example, source your own mode-600
credential file with `set -a; source /absolute/path/private/credentials.env;
set +a`. Never put key values in the notebook, JSON, shell script or repository.
Preflight reports only key names and whether they are present; authentication is
not proved until the service accepts a request.

Start Jupyter from the copied notebook directory, using the exp interpreter:

```bash
cd /absolute/path/my-pet-project/notebooks
/absolute/path/siderius-exp/.venv/bin/python -m jupyterlab
```

Select that environment's Python kernel. The notebook checks the interpreter.

## 4. Edit, review, then run

Follow the notebook in order. It shows transformed images and manifests before
asking you to edit settings. Initial values are three research iterations, two
tuner rounds, 32-epoch ceilings, Trial training/validation fractions of 0.5,
Formal fractions of 1.0, Trial/Formal time ceilings of 2/5 minutes and 8 GiB VRAM.
These are demo settings, not framework defaults or expected runtimes.

There are 370 training, 74 validation and 370 independent final images. Validation
feeds the agent; final is not run here. Pet requires `train_portion=1`, disabling additional per-epoch subsampling.
Trial/Formal fractions choose the attempt scope first. The generated training
configuration still controls batching; `drop_last=True` omits an incomplete last
batch. Inspect its saved config and loader counts for exact samples per epoch. The optional notebook resplit example saves a **new** task with
333 training and 111 validation images while preserving final membership.

Before the first run, inspect all saved values and execute this preview:

```bash
bash /absolute/path/my-pet-project/scripts/run-pet.sh
```

It prints the native command, exact revisions, strategy identity, split counts,
input hashes and required key presence. It makes no API calls or CUDA allocation.
A missing dataset, dirty/mismatched checkout or incomplete environment produces
an error before execution. To also check native launcher argument parsing:

```bash
bash /absolute/path/my-pet-project/scripts/run-pet.sh --dry-run
```

Then either use Run All in the notebook or execute the **same saved script**:

```bash
bash /absolute/path/my-pet-project/scripts/run-pet.sh --launch
```

This performs paid LLM calls and GPU work. The notebook delegates to that command,
records a console log and stops the process group if interrupted or timed out.
Its 60-minute timeout is not a billing cap; set spending controls for your own
account. The per-attempt time/VRAM settings do not limit total API expense.

Data Analysis, literature review and human advice are disabled in this fixed
workflow. There is no workflow sandbox to configure; native generated-code
execution checks still apply.

## 5. Read your results and rerun deliberately

The notebook plots Formal scores from `runs/pet_demo_001/`. Filled points passed
recorded Health checks, hollow points have scores but failed checks, and attempts
without scores remain unscored. No Health PASS or high accuracy is required to
teach this workflow. A run with no measured Formal scores cannot produce a
meaningful score chart; inspect the log instead of treating it as zero accuracy.

`plots/pet_demo_001/` receives `score-versus-iteration.png`, `.svg` and `.csv`.
The notebook reuses a completed run only while all saved task/config/script inputs
match its receipt. To change parameters and run again, save a new `run_name` and
`workspace` in the experiment JSON. Keep the previous files for comparison.
Interrupted directories are not silently resumed.

## Recorded example

The [qualified three-iteration example](example/README.md) includes real images,
the score chart, Trial/Formal outcomes and provenance. These pictures are also
embedded in the notebook for GitHub readers. They are demonstration outputs;
initialization clears them from your copied notebook. Executing that copy reads
your own project and produces your own results.

![Pet training input examples](example/images.png)

![Pet Formal score versus iteration](example/score-versus-iteration.png)
