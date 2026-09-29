# Learn a paper task, then run it from a script

Start with **TESS near-core rotation regression**. The notebook walks through
the task's data, model contract, metric and settings. The terminal script runs
the existing fixed workflow. You can close the notebook while the script runs.

This is a self-contained teaching entrypoint inside siderius-exp, not a second
copy of the framework or task implementations. You need access to both Git
repositories. Keep data, credentials, edited notebooks and outputs outside them.

| Paper task | Tutorial status | Existing task |
|---|---|---|
| TESS | Notebook, pinned download/staging, editable demo and formal entrypoint | [Task package](../../tasks/phyts_tess/README.md) |
| LIGO | Next task; no runnable notebook here yet | [Task package](../../tasks/phyts_ligo/README.md) |
| Project 8 | Next task; paper uses the time/frequency four-channel variant | [Dual representation](../../tasks/phyts_project8/DUAL_REPRESENTATION.md) |
| TIDMAD | Next task; four independent bands | [Task package](../../tasks/tidmad/README.md) |

The demo teaches configuration and execution. Fresh LLM searches need not
produce the paper's exact models or scores. Four fixed-workflow tutorials will
not reproduce the coding-agent/orchestration comparisons or retrospective
behavioral reviews. Archived-checkpoint replay is a separate reproduction path.

## 1. Install in the two exact checkouts

Use Linux and Python 3.12. The teaching launcher accepts one RTX 5090 or H100
with a working NVIDIA driver and the locked CUDA PyTorch installation. AMD,
Intel GPU and CPU execution are not supported. The TESS paper deployment used
RTX 5090 with an 8 GiB model budget; H100 is an additional tutorial route.

From your siderius-exp checkout:

```bash
export EXP_CHECKOUT="$(pwd -P)"
uv sync --python 3.12 --group dev --group tutorial --frozen

# Choose a NEW sibling checkout, outside the exp checkout.
export INFRA_CHECKOUT="/absolute/path/to/SIDERIUS-tutorial"
git clone git@github.com:Galileo-Sandbox/SIDERIUS.git "$INFRA_CHECKOUT"
git -C "$INFRA_CHECKOUT" checkout --detach "$(cat "$EXP_CHECKOUT/SIDERIUS_REVISION")"
(cd "$INFRA_CHECKOUT" && uv sync --python 3.12 --group dev --frozen)
```

The exp environment runs notebooks and preparation tools; the infra
environment executes the research loop. Neither borrows the other's
`site-packages` or uses `PYTHONPATH`. Both source checkouts must be clean at
preview/launch time. Do not edit the version pin to work around a refusal.

## 2. Open an editable notebook outside source

Choose an external tutorial directory; use the same path throughout:

```bash
export TUTORIAL_HOME="/absolute/path/to/tess-tutorial"
mkdir -p "$TUTORIAL_HOME"
cp "$EXP_CHECKOUT/tutorials/paper/notebooks/01_tess_tutorial.ipynb" "$TUTORIAL_HOME/"
"$EXP_CHECKOUT/.venv/bin/python" -m ipykernel install \
  --prefix "$EXP_CHECKOUT/.venv" --name siderius-exp-tutorial \
  --display-name "SIDERIUS exp tutorial"
"$EXP_CHECKOUT/.venv/bin/jupyter" lab --ServerApp.root_dir="$TUTORIAL_HOME"
```

Open `01_tess_tutorial.ipynb` and select **SIDERIUS exp tutorial**. The notebook
verifies its interpreter. Default Run All reads source and displays settings;
it downloads nothing and starts no run. Two optional file-writing exercises
are disabled until you enable them.

## 3. Prepare only the permitted data

Run in a terminal from the exp root:

```bash
cd "$EXP_CHECKOUT"
.venv/bin/python -m tutorials.paper.prepare_tess \
  --raw-dir "$TUTORIAL_HOME/raw-tess" \
  --data-dir "$TUTORIAL_HOME/tess-data"
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

## 4. Configure keys without storing them in a notebook

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
same launching shell. Do not enter keys in notebook cells, settings JSON,
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

The historical model ID is retained. If your account cannot use it, copy
`agents.json` to the external tutorial directory and select an available model
there, as shown in the notebook. That is a new model treatment, not an exact
paper rerun. Key presence does not prove provider access; only a request can.

## 5. Preview, launch, inspect

The notebook writes external `tess-demo.json` after you opt in. Alternatively,
copy [tess_demo.json](configs/tess_demo.json) and replace all absolute paths.
Choose `gpu: "RTX 5090"` or `gpu: "H100"` and a new workspace path:

```bash
bash "$EXP_CHECKOUT/tutorials/paper/scripts/run.sh" \
  --config "$TUTORIAL_HOME/tess-demo.json"

# Starts paid API calls and model training:
bash "$EXP_CHECKOUT/tutorials/paper/scripts/run.sh" \
  --config "$TUTORIAL_HOME/tess-demo.json" --launch
```

Preview validates source pins, routing and composition and prints JSON. It
needs no credentials, prepared data or GPU. Launch additionally checks keys,
both staged populations, hashes, GPU name/capacity and an actual CUDA allocation
in infra's environment. It refuses root execution.

The default demo runs one iteration with one Trial and one Formal opportunity,
one-epoch ceilings, 2/5-minute attempt budgets and an 8 GiB VRAM budget. A
candidate can fail validation or training; a Formal score is not guaranteed.
Attempt budgets are not a total wall-clock or API-spend cap. This teaching
entrypoint has no six-hour campaign supervisor.

The sibling `<workspace>.tutorial.json` records settings, command, revisions,
composition identity, routing digest and data digests without secrets. Node
records live under the workspace. The notebook shows how to inspect them.
A high score is not a demo pass rule: inspect exit status and failure records.
The terminal owns the run. Use its interrupt/stop mechanism, then inspect the
outcome before retrying. This wrapper only starts fresh runs.

## 6. Change settings or hardware deliberately

| Change | Where | Effect |
|---|---|---|
| Iterations, epochs, time, VRAM | External `tess-demo.json` | New demo schedule/budgets |
| RTX 5090 ↔ H100 | `gpu` and suitable `vram_gib` | New hardware run; launcher checks physical card |
| Provider/model | External routing JSON selected by `llm_config` | New model treatment and possibly new required keys |
| Task description | Copy of the whole task package selected by `composition` | New fingerprint; notebook demonstrates a controlled edit |
| Input length, split, metric, Health | Task declaration **and** runtime/tests | Qualify the changed task; not an arbitrary launcher override |

For **another NVIDIA GPU**, first verify that locked PyTorch can allocate a
CUDA tensor on it. Choose a VRAM budget below physical capacity; review RAM,
disk and time budgets. Add the card name explicitly to `DemoSettings.gpu`,
extend the hardware tests/qualification evidence, commit the change, and run
a short fresh demo. Unknown GPUs are refused until that work is done. Do not
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
  --data_dir "$TUTORIAL_HOME/tess-data" \
  --unit_dir "$TUTORIAL_HOME/new-paper-unit" \
  --run_name tess_paper_rerun_001 --arm no-prior
```

Review its preview before adding `--launch`. That route owns the immutable
six-hour clock, restart behavior and original settings; it does not read demo
JSON. The current pin includes fixes after some historical runs. Exact archived
replay needs that run's source pair, checkpoints and evidence, not just this
command. Support-code contracts and validation ownership are documented in
[implementation.md](implementation.md).
