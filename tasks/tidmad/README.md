# Example pack — `tidmad` (Track A: SQUID / TIDMAD time-series denoising)

The original SIDERIUS scientific task, projected as a user-facing example
pack (roadmap `docs/design/siderius_generic_framework_upgrade.md` §22.9 Track A,
§22.23.2). It is the persistent scientific-compatibility control: every later
Step keeps its strongest Stage-A evidence on this task.

> **New here?** This is one of three example task packages that show what a
> SIDERIUS task looks like. Start with
> [what a task must provide](../../docs/concepts/task-package.md); see
> [supported tasks and current maturity](../../docs/concepts/supported-tasks.md)
> for how the three compare.
>
> **Maturity**: ✅ TIDMAD runs the full agent loop end-to-end through the
> production chain. This *pack* is a read-only projection of that plus a thin
> entrypoint — it contains no framework code. See `STATUS.md`.

---

## Quickstart

This section is the whole journey: what ships in the repository, what you must
obtain yourself, how to point the framework at it, the one command to run, and
how to look at the result.

### 1. What ships in this repository

Everything needed to *understand* and *bind* the task is already here — no raw
data is, and none ever will be.

| shipped asset | path | what it is |
|---|---|---|
| qualification composition | `compositions/bounded_qualification.yaml` | reusable task-owned scope selected by the qualification experiment |
| literature-review config | `framework_configs/lit_review.yaml` | TIDMAD root paper, search posture, and confidence rubric used when literature review is enabled |
| resolved declarations | `resolved/*.json` | dataset profile, model I/O contract, deliverable spec, metric spec, file identity |
| scoring anchor map | `reference_data/segment_anchors.json` | the metric's normalisation constants — **nothing to precompute** |
| reference artifacts | `reference_data/raw_baseline/`, `reference_data/ground_truth/`, `reference_data/official_paper_result/` | metric floor, metric ceiling, paper-comparable scores |
| reference loader | `runtime/reference_scores.py` | task-owned loading and validation of the frozen floor, ceiling, and ruler |
| paper-spec baselines | `ml_models/legacy_baseline_configs.json` | the TIDMAD paper's hyperparameters |
| the qualification entrypoint | `../../experiments/tidmad/two_iteration_qualification/launch.sh` | experiment-owned workflow treatment |

### 2. The external data dependency

The TIDMAD HDF5 files are **not** distributed with SIDERIUS and are **not**
downloaded by anything in this pack. They come from the paper's own
distribution:

- paper: *TIDMAD: Time Series Dataset for Discovering Dark Matter with AI
  Denoising* — <https://arxiv.org/abs/2406.04378>
- official distribution: <https://github.com/jessicafry/TIDMAD>, whose
  `download_data.py` / `filelist.dat` retrieve the files from the OSDF caches
- licence: CC BY 4.0 (see `PROVENANCE.md`; consult the source for the
  authoritative current terms)

> **There is no `fetch_tidmad` tool in this repository, and this README will
> not pretend otherwise.** The contrast packs ship fetchers
> (`tools/example_packs/fetch_davis.py`,
> `tools/example_packs/fetch_oxford_iiit_pet.py`) because their datasets have a
> stable direct download; TIDMAD's acquisition is owned by the paper's
> repository, so this pack *points* at prepared data instead of preparing it.

### 3. Preparation — stage the files, then point at them

Run the paper repository's downloader into any directory you choose. SIDERIUS
reads two file families from it:

```text
abra_training_0000.h5 … abra_training_0019.h5
abra_validation_0000.h5 … abra_validation_0019.h5
```

Full staging is ~50 GB. `resolved/identity.json` lists every expected filename;
the naming patterns themselves are owned by
`execute_tools/dataset_config.py`, not by this pack.

There are two ways to name that directory, and they are the same value:

| mechanism | scope | use it when |
|---|---|---|
| `--data_dir <dir>` on the command below | this run | always — a published command should carry its own inputs |
| `tidmad_data_dir:` in `tidmad_data_config.yaml` | this machine, every run | you have set the machine up permanently (`cp tidmad_data_config.example.yaml tidmad_data_config.yaml`) |

Both resolve through `execute_tools/data_paths.py`, which validates the
directory at launch — before any LLM call or GPU minute is spent. See
`data/README.md`.

### 4. Preview the run

`--dry-run` walks the chain and prints the exact child command without
executing anything. Do this first.

<!-- QUICKSTART-PREVIEW-COMMAND -->
```bash
bash experiments/tidmad/two_iteration_qualification/launch.sh \
    --siderius-checkout /path/to/SIDERIUS \
    --workspace /path/to/your/workspace \
    --data_dir /path/to/tidmad/data \
    --dry-run
```

### 5. Run it

<!-- QUICKSTART-RUN-COMMAND -->
```bash
bash experiments/tidmad/two_iteration_qualification/launch.sh \
    --siderius-checkout /path/to/SIDERIUS \
    --workspace /path/to/your/workspace \
    --data_dir /path/to/tidmad/data
```

`--siderius-checkout`, `--workspace`, and `--data_dir` are **required and have
no defaults**. The task package names its framework checkout, output location,
and dataset explicitly instead of depending on repository co-location or a
directory that happens to exist on one machine.

The experiment launcher is a thin adapter. It resolves this task package from its own
location, validates the explicitly selected framework checkout and inputs, and
then executes that checkout's normal production launcher:

```text
experiments/tidmad/two_iteration_qualification/launch.sh
  → <siderius-checkout>/sdsc_submission_scripts/run_chain.sh --task_composition <siderius-exp>/tasks/tidmad/compositions/bounded_qualification.yaml
  → sdsc_submission_scripts/run_one_iteration.py
  → the same workflow, declarations and plugins that CI and the Gates exercise
```

It applies one bounded posture so a first run is cheap. Every value is an
ordinary launcher flag; passing the same flag yourself overrides it, and every
other launcher argument is forwarded verbatim. `bash
experiments/tidmad/two_iteration_qualification/launch.sh --help` prints the contract.

| default applied | why |
|---|---|
| `--mode lilab` | foreground subprocess |
| `--task_composition <siderius-exp>/tasks/tidmad/compositions/bounded_qualification.yaml` | binds the reusable task-owned qualification scope, not a Gold campaign |
| `--run_name tidmad_quickstart` | pins the run id |
| `--llm_config <repo>/llm_configs/openai_tiered_pro.json` | per-node model routing. Without it the run falls back to a single default model with no routing. Override with `--llm_config llm_configs/deepseek_tiered_pro.json` or your own file |
| `--ml_lit_review_config <siderius-exp>/tasks/tidmad/framework_configs/lit_review.yaml` | keeps TIDMAD-specific literature framing in the experiment repository even when the CLI enables or disables the advisor |
| `--start_iter 1` | **not cosmetic — see below** |
| `--num_iterations 2` · `--max_rounds 2` · `--max_epochs 1` | proves iteration-state continuity and executes one Trial plus one Formal round per iteration |
| `--min_formal_batch_size 1` | preserves Trial/Formal batch parity in this qualification workflow |
| `--trial_portion 0.02` · `--formal_portion 0.02` · `--formal_eval_portion 0.02` | see below |
| `--trial_time_budget_minutes 20` · `--formal_time_budget_minutes 60` | **TIDMAD-priced — see below** |

**Why `--start_iter 1`.** Auto-resume is on by default, and on an *existing*
workspace the launcher takes its start iteration from
`scripts/inspect_run_state.py --next-iter`. That capture can be polluted by
plugin-loader output on stdout; the corrupted value then reaches `seq`, the
iteration loop body never runs, and the chain still prints
`"<N> iterations walked"` — computed from the number you *requested*, not the
number actually walked — and exits `0`. A published command must not be able
to do nothing and report success, so this one pins iteration 1. To resume
deliberately, pass `--start_iter N` yourself; it overrides this default.

**Why the portions deviate from the chain's defaults.** TIDMAD's sampling unit
is a 10 000 000-sample PSD segment, and each of its 20 files holds 200
segments; at `0.02` each full-scope phase reads approximately 80. Formal
evaluation is pinned separately because the production launcher's default is
the complete evaluation scope. Leaving that default in a bounded quickstart
would make its advertised data and time bounds inconsistent. These ordinary
task-agnostic knobs bound the run without silently dropping files.

**Why the time budgets are here.** Passing a time budget switches on the
wall-time pre-flight, which prices the training workload through **TIDMAD's
dataset topology** (`psd_segment_length // segmentation_size`). TIDMAD declares
that topology, so the estimate is meaningful, and the flags earn their place:
a planner-chosen portion can otherwise produce a multi-hour round.

A task that declares no such topology now takes a **named inapplicable path** —
the pre-flight is skipped with a stated reason and the run continues, rather
than failing before training. So the other packs simply have no use for these
two flags, not a hazard from them.

You also need at least one LLM API key in the selected SIDERIUS checkout's
`.env` and a CUDA GPU.

**Bounding it further, TIDMAD-specifically.** `--data_scope 4-9` (paired with
`--health_gate_files`, which must be a subset of the scope) restricts the run
to a subset of files, so you need only those staged. This is a partition-index
concept from *TIDMAD's own topology*: a composed task that declares no such
topology has `--data_scope` refused by name and expresses coverage through its
own scope capability instead. That is why the quickstart's own defaults use the
task-agnostic portion knobs, and why this flag is documented here rather than
baked in.

### 6. Where the output goes

Everything lands under the `--workspace` you named — nothing is written into
this tracked example tree:

```text
<workspace>/iter_001/…                     per-iteration node output records
<workspace>/health_checks_effective.yaml   the pinned effective health config
<workspace>/run_invariants_lock.json       the resolved scope / config identity
```

### 7. Inspect the result

<!-- QUICKSTART-REPORT-COMMAND -->
```bash
python -m tools.run_report --workspace /path/to/your/workspace --out /path/to/report
```

This renders the run's summary, objective / metric trajectories and plots from
the records the chain already persisted. The dashboard
(`python dashboard/main.py`) is the live alternative.

### If it refuses

Most first-run failures are deliberate refusals. The experiment launcher names the
missing input; beyond that, the table in
[operating a run](../../docs/guides/operating-a-run.md#failures-and-refusals)
maps each refusal to its cause.

---

## Task

Full-spectrum 1-D time-series denoising of SQUID dark-matter detector data
(ABRACADABRA / TIDMAD): map a noisy `[B, T] int64` signal to a clean
`[B, 256, T] float32` per-timestep class reconstruction, decoded by argmax.

| aspect | value | owning path (edit THERE, never here) |
|---|---|---|
| task description / forward contract | prose + model I/O declaration | `declared/task_config.yaml` |
| model I/O contract | `[B, T] int64 → [B, 256, T] float32`, `class` axis fixed 256 → categorical | `resolved/model_io_contract.json`, bound by the task composition |
| dataset profile | 20 validation files, 200 × 10 000 000-sample segments per file, 10 MS/s, `channel0001` input / `channel0002` truth, int8 storage +128 offset, 256 classes | `resolved/dataset_profile.json` |
| deliverable | per-file HDF5 `abra_validation_denoised_{file_index:04d}.h5` | `compositions/bounded_qualification.yaml` and `runtime/tidmad_data_path.py` |
| golden metric | `tidmad_denoising_score` · direction **higher** · anchor-normalised linear grand mean, log base 5.27 (frozen paper-comparable formula) | `resolved/metric_spec.json`, implemented by the pinned framework metric plugin |
| health policy | HealthGate checks at tuner round boundaries | `framework_configs/health.yaml` |
| training observation (Step 07a) | **R1** = the run-resolved training objective (`loss_config.loss_type` — a loss family is a run choice, not task semantics; identified on the record by `objective_kind` + `objective_config_fingerprint`); **R2** = per-epoch mean training objective (`loss_history`); **R3** = the SAME computation on the run-bound validation scope (the tuner's `eval_sample_set`, VALIDATION file family `abra_validation_*`), no backprop — **production-backed from 07a**; optional checkpointed observations: none declared. Persisted as `ExperimentRecord.training_history` / `.training_diagnosis` (per-run evidence, not task config — no `resolved/` snapshot); hidden from the planner / reflector until 07b | `execute_tools/train_engine_sandbox.py` (R3 pass), `execute_tools/training_history.py`, `agent/schemas/training_diagnosis.py` |
| data root | machine-local, gitignored `tidmad_data_config.yaml` | `execute_tools/data_paths.py` — see `data/README.md` |
| reference artifacts | anchors, raw baseline, ground truth, official paper scores | `reference_data/` |

## What this pack demonstrates at PR0

`resolved/` holds **READ-ONLY resolved snapshots** of the five contracts above
(`dataset_profile`, `model_io_contract`, `deliverable_spec`, `metric_spec`,
`identity`), **GENERATED** from the production authorities by
`tools/example_packs/projection.py`. **DO NOT EDIT them — the runtime does not
read these files as an authoring surface.** To change the task, edit the owning
path in the table;
CI (`tests/unit/examples/test_tidmad_projection.py`) regenerates every
snapshot and deep-compares it, so a drift is a red test resolved by
regenerating in the same commit as the authority change
(`.venv/bin/python -m tools.example_packs.projection`).

One nuance worth knowing before you edit anything here: since the shipped
composition manifest exists, `configs/task_composition/tidmad.yaml` *binds*
`resolved/dataset_profile.json` and `resolved/metric_spec.json` as its
declaration references, so a composed run does load those two. That does not
make them an editing surface — it is precisely why a hand edit is caught as a
red test rather than being harmless.

The task description, forward-contract prose and health config are
**referenced**, not copied: their owning YAML files are the authority and a
copy here would be the parallel authority roadmap §22.23.1 forbids.

## Other ways to run

The qualification experiment launcher is the documented bounded command, not the only way in.
Runs also go through the normal SIDERIUS interfaces documented for operators
([`docs/getting-started/first-run.md`](../../docs/getting-started/first-run.md),
[`docs/guides/operating-a-run.md`](../../docs/guides/operating-a-run.md),
[`docs/reference/entrypoints.md`](../../docs/reference/entrypoints.md), and
`scripts/run_comparison.py` for the TIDMAD-only baseline comparison harness) —
see `STATUS.md` for what is and is not projected here yet.

## Files

```text
README.md          this file
compositions/      reusable task-owned composition scopes
PROVENANCE.md      data source, licence, reference artifacts, data-root mechanism
STATUS.md          honest maturity + the seams not yet projected (mirror of the roadmap)
data/README.md     how the machine-local data root is configured (no data here)
resolved/          GENERATED read-only snapshots + DO-NOT-EDIT banner
```
