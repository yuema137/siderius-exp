# TIDMAD task package

TIDMAD is the task package for denoising long SQUID detector time series. One
example is a long waveform segment. The model receives the noisy signal and
returns one continuous denoised value for every time step in the current
continuous-regression workflow. Historical classification compositions remain
available and are identified separately below.

This directory defines what the data means and how a prediction becomes a
score. It does not choose the number of research iterations, Trial/Formal
budgets, provider models, or the machine on which a run executes. Those choices
belong to an experiment under `experiments/tidmad/`.

## The data contract in one minute

Here `B` is batch size and `T` is the model's time-window length. A PSD
segment is the long waveform interval used to estimate a power spectrum;
the model processes shorter windows within that interval.

| Item | Current declaration |
| --- | --- |
| Files | `abra_training_0000.h5` … `abra_training_0019.h5` and the matching validation files |
| Dataset files | 20 file indices, each with a training and validation file (40 HDF5 files total). A main run selects `0-3` (4 pairs), `4-9` (6 pairs), `10-14` (5 pairs), or `15-19` (5 pairs) |
| Examples per file | 200 PSD segments |
| Raw segment | 10,000,000 samples at 10 MHz |
| Model segment | Caller/model configuration chooses `segmentation_size`; the fixed ICLR workflow requires 40,000 |
| Input channels | `channel0001` is the noisy SQUID readout; `channel0002` is the injected clean target |
| Model input | `[B, T]` integer-coded samples. The profile declares `int8` storage, `int16` arithmetic and offset `+128` to obtain codes 0–255; the model boundary accepts `int64` or `int32` |
| Model output | `[B, T]` `float32` continuous waveform; there is no class axis and no `argmax` |
| Stored deliverable | `.h5`, prefix `abra_validation_denoised`, `int8` storage with the task's offset codec |
| Primary score | `tidmad_denoising_score`, higher is better |
| Blocking Health | `amplitude_collapse` remains the blocking collapse check; other health values are recorded for diagnosis |

The raw HDF5 files are never committed here. Put them in an external,
read-only data directory and pass that directory with `--data_dir`.

## Which file owns which decision?

This is the practical map. Change the owning file, then create a new experiment
identity and qualify it. Do not copy a value into a launcher just to override
the task's authority.

| If you want to change… | Change or add… | Do not change… |
| --- | --- | --- |
| Which HDF5 root is used | The experiment command's `--data_dir` | This repository's Python code |
| Which band is exposed | The experiment's `--band` (`0-3`, `4-9`, `10-14`, `15-19`) | A second hard-coded file list in the task |
| Training/validation file names and topology | `resolved/dataset_profile.json` through its owning declaration/projection, plus provenance and tests | A launcher-only file pattern |
| The fixed 20-of-200 training parent | A new pool declaration and matching data-path implementation; the current manifest digest and 0.1 source fraction are enforced in `TidmadFrozenPoolDataPath` | Only the JSON or `--formal_portion`; neither alone changes the frozen pool |
| Task meaning and model I/O | `declared/task_config_regression.yaml` | `workflow.json` or advice text |
| Primary score and direction | `resolved/metric_spec.json` and `runtime/scoring.py`, in one reviewed task change | A secondary score or a dashboard ordering rule |
| Output filename and storage encoding | The composition's `deliverable` block, `resolved/dataset_profile.json` encoding, and `runtime/output_conversion.py`; synchronize the deliverable snapshot | Candidate code, a shell rename, or the snapshot alone |
| Blocking/recording Health checks | `framework_configs/health_regression.yaml` and the referenced runtime checks | Framework policy or the model prompt |
| What the proposer/implementor is told about the science | `framework_configs/proposal_regression.yaml`, `interpretation.yaml`, or `implementor.yaml` | An experiment budget file |
| Literature search rules | `framework_configs/lit_review.yaml` | The generic infra repository |
| Reference anchors and baseline/ceiling rulers | `reference_data/segment_anchors.json`, `raw_baseline/`, `ground_truth/` | A run-local copy without a new identity |

The files under `resolved/` are committed projections used by the composition.
They are not a convenient scratch area. An intentional change must update its
owning declaration, regenerate or re-project the snapshot, update provenance,
and pass the task tests. Editing a generated JSON alone creates an ambiguous
task identity.

## File-by-file package map

### 1. Composition files: what SIDERIUS loads

Choose one composition explicitly in the experiment:

| File | Use |
| --- | --- |
| `compositions/continuous_regression_frozen_pool.yaml` | Main ICLR-style workflow. Uses the continuous waveform contract and the fixed 20-of-200 training parent. |
| `compositions/continuous_regression.yaml` | Reusable continuous-regression task without the frozen parent binding. Use only when the experiment intentionally owns a different training scope. |
| `compositions/bounded_qualification.yaml` | Historical classification contract selected by the two-iteration qualification launcher; not the current regression workflow or a paper-scale campaign. |

Each composition connects the task data path, dataset profile, metric,
scoreability contract, Health, task prompt blocks, task configuration, and
deliverable naming. The experiment adds workflow settings around that task
composition; it does not rewrite these declarations.

### 2. Scientific declarations

| File | What it sets |
| --- | --- |
| `declared/task_config_regression.yaml` | Plain-language task description, `[B,T]` input, `[B,T]` continuous output, admissible dtypes, segmentation semantics, and regression guidance |
| `declared/frozen_training_pool_v1.json` | Seed `20260916`, 20 selected segment indices for every file, 10% parent (`20/200`), 10,000,000-sample PSD length |
| `resolved/dataset_profile.json` | 20-file topology, 200 segments/file, 10 MHz rate, channel names, encoding metadata, and Health peek files |
| `resolved/model_io_contract.json` | Historical classification snapshot with `[B,256,T]` output; not selected by the continuous-regression compositions. Their live contract comes from `declared/task_config_regression.yaml` |
| `resolved/metric_spec.json` | `tidmad_denoising_score`, higher-is-better, anchor-normalized log aggregation, and required deliverable attributes |
| `resolved/deliverable_spec.json` | Reference snapshot of output naming and encoding; live naming comes from the composition and storage encoding from the dataset profile |
| `resolved/identity.json` | Reference snapshot of file families and indices; the runtime adapter reads the bound dataset profile |

### 3. Prompt and validity declarations

| File | What it sets |
| --- | --- |
| `framework_configs/proposal_regression.yaml` | Task-specific proposal guidance, including the continuous-output contract |
| `framework_configs/interpretation.yaml` | What an interpreter may use when explaining task evidence |
| `framework_configs/implementor.yaml` | Model-code implementation instructions |
| `framework_configs/health_regression.yaml` | TIDMAD Health roster, thresholds, peek files, and blocking/recording disposition |
| `framework_configs/lit_review.yaml` | Root papers, search rounds, evidence requirements, and literature channel settings |

### 4. Runtime implementations

| File | Called when… |
| --- | --- |
| `runtime/tidmad_data_path.py` | Training, validation, inference input materialization, and deliverable read/write are requested |
| `runtime/scoring.py` | A persisted denoised waveform is converted into the canonical score |
| `runtime/scoreability.py` | The candidate output is checked before scoring |
| `runtime/output_conversion.py` | A continuous `[B,T]` prediction is converted to task storage bytes |
| `runtime/profile.py` | The task dataset profile and topology are resolved |
| `runtime/anchor_map.py` | Anchor normalization data is read or built |
| `runtime/reference_scores.py` | Raw and ground-truth reference rulers are loaded |
| `runtime/campaign_artifacts.py` | Task-owned campaign artifacts are located and verified |

### 5. Reference data and tools

`reference_data/segment_anchors.json` contains the committed normalization
ruler. `reference_data/raw_baseline/` is the no-denoising floor,
`reference_data/ground_truth/` is the task ceiling, and
`reference_data/official_paper_result/` stores paper-model comparison records.
`tidmad_signal_frequencies.txt` records the injected-frequency reference.
These files are scientific evidence, not a replacement for the external HDF5
data root.

The scripts in `tools/` compute or render reference artifacts and comparisons.
Inspect each script's output arguments and defaults before running it; select
an external output directory and preserve the frozen reference files.

## How a fixed workflow calls this package

For one band, the path is:

1. `experiments/tidmad/main_fixed_workflow/preflight.py` checks the selected
   band, HDF5 checksums, staged `segment_anchors.json`, experiment pin, and
   framework pin.
2. The launcher passes `tasks/tidmad/compositions/continuous_regression_frozen_pool.yaml`
   to SIDERIUS with `--data_dir`, `--data_scope BAND`, and
   `--health_gate_files BAND`.
3. SIDERIUS loads the composition and binds the task data path, model I/O,
   metric, scoreability, Health, and prompt blocks.
4. The generated model receives integer `[B,T]` input and must return
   continuous `[B,T]` float32 output.
5. The task data path writes indexed HDF5 deliverables using the declared
   output codec.
6. Scoreability checks the deliverable, the metric reads it and computes the
   anchor-normalized score, and Health records or blocks according to the
   task Health roster.
7. The experiment records the task tree, configuration hashes, data hashes,
   score, Health results, and framework/exp revisions in its external workspace.

The task does not read a different band because the launcher exposes only the
selected HDF5 pair set. `band_inputs.py` rejects unexpected files and checks
the approved manifest before the chain starts.

## Safe customization recipes

### Use a different band

Keep the task package unchanged. Prepare an external directory containing only
that band's training/validation HDF5 pairs and the approved anchor file, then
pass `--band 10-14` (or another supported band) and that directory to the
experiment preflight and launcher.

### Use a different segment parent

Create a new declared pool JSON and a new composition or experiment treatment.
Do not edit `frozen_training_pool_v1.json` in place if you need to preserve the
ICLR identity. Update the pool seed, selected indices, source portion, and
provenance together. The current `TidmadFrozenPoolDataPath` also pins the
manifest SHA-256 and requires a 0.1 source fraction. Bind a matching task
implementation and test it; replacing the JSON alone will be refused.
The resulting run is a new treatment and cannot be mixed with old scores as
if the parent pool were unchanged.

### Change model window length

This is a model/workflow change, not a data-file rename. Change the experiment
parameter that supplies `model_config.segmentation_size`, then rerun preflight
and qualification. The task adapter derives the segment layout from the
resolved candidate configuration; it does not silently choose a default.

### Change the score or Health policy

Change the task-owned declaration and its runtime implementation together,
update reference/provenance files, and start a fresh experiment identity. Never
patch a score in a result file or replace a Health result in a launcher.

## Quickstart

The following previews the historical classification qualification. For the
current regression workflow, use the linked fixed-workflow steps below.
Use a fresh external workspace:

```bash
bash experiments/tidmad/two_iteration_qualification/launch.sh \
  --siderius-checkout /absolute/path/to/SIDERIUS \
  --workspace /absolute/path/to/fresh/workspace \
  --data_dir /absolute/path/to/tidmad/data \
  --dry-run
```

For the fixed one-band workflow, use the experiment README and run its
`preflight.py` before `launch.sh`. Raw HDF5 files, credentials, workspaces,
checkpoints, and reports stay outside this repository.

## Boundaries

The old `examples/tidmad` projection is historical and is not an authoring or
launch surface. A new run must select this task explicitly; no task is inferred
from a directory name.

## Learn one band and hold out different file ranges

The [one-band tutorial](../../tutorials/paper/tidmad/README.md) copies this task
into an external user project. It teaches where task/experiment/script files
live and how to inspect saved changes before launching. Its new file-holdout
example uses training indices 0–1, workflow-validation index 2 and final-test
index 3, with adjustable Trial/Formal proportions and budgets. All original
segments remain eligible within assigned files; this is file-range separation,
not per-frequency labeling. The original frozen paper-pool example remains
separate. Shared 5090 users reuse existing large files; other users download
only the required band. Neither route changes repository task templates.
