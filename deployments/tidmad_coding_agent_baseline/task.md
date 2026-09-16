# TIDMAD coding-agent baseline

You have 24 hours on one NVIDIA H100 to obtain the strongest **scientifically
valid** TIDMAD denoising result you can. Work autonomously for the full budget.
At the start of every invocation, inspect the existing files and results in
your workspace and continue from them instead of starting over.

The clock starts only when the supervisor launches this evaluated run. A CLI
exit, process restart, service restart, or machine restart does not reset or
extend it. Environment and data preparation completed before that launch is
outside the 24-hour evaluation window.

## What you have

- `/work/input/tasks/tidmad/`: the agent-visible view of the frozen TIDMAD task
  definition, model I/O contract, Health contract, public reference material,
  and scientific documentation. Evaluator-only assets are intentionally absent.
- `/work/input/treatment.json`: the frozen record of which optional information
  is present for this run. If its advice mode is `enabled`, the one human-advice
  artifact is `/work/input/advice.json`; if the mode is `disabled`, no human
  advice was supplied. No other file is an implicit advice source.
- `/data/public-training/`: all 20 labelled training HDF5 files.
- `/usr/local/bin/tidmad-score`: the complete-band candidate-scoring entry point.
- `/work/agent/`: your writable scientific workspace.
- `/baseline/agent/environments/runtime/`: a prepared Python environment with
  PyTorch, HDF5, NumPy, and SciPy; you may use, extend, or replace it.
- `/work/input/inference-requirements.txt`: the packages used by the immutable
  evaluator-owned runtime that executes submitted models.

Read the frozen task package before designing models.

The original scientific reference is *TIDMAD: Time Series Dataset for
Discovering Dark Matter with AI Denoising*, J. Fry et al., arXiv:2406.04378
(https://arxiv.org/abs/2406.04378). The task package's `PROVENANCE.md` records
the canonical citation and public upstream repository.

## Scientific objective

Search independently for each of the four bands: `0-3`, `4-9`, `10-14`, and
`15-19`. The four winning architectures may differ. Higher TIDMAD raw score is
better among candidates that pass the scientific validity contract below.

This is a supervised denoising task. Each training HDF5 file contains a noisy
detector time-series input and its clean target. A candidate must transform a
previously unseen noisy input into a denoised time series with the shape and
fields required by the frozen model-I/O and deliverable contracts.

The evaluated solution must be a trained ML denoising model. Its only inference
input is an evaluator-created batch of raw, non-overlapping 40,000-sample
segments. Segmentation, file handling, ADC offset conversion, output decoding,
reassembly, and HDF5 writing are fixed evaluator operations; candidate-specific
free-form preprocessing or postprocessing outside the submitted model is not
part of this task.

An eligible submission is a trained ML model fitted from the provided labelled
training data. Its only inference input is the evaluator-provided raw segment
tensor described above. Model architecture, fitting method and research process
are not prescribed by this task; eligibility is determined from the submitted
artifact, fixed interface, scoring contract and Health evidence.

The exact injected frequencies, scoring anchors, official validation inputs,
and official validation truth are not part of the information available to the
research condition. The evaluator owns those files and supplies only raw
40,000-sample segment tensors to the frozen submitted model. It enforces that
boundary through the mounted filesystem and the scoring interface.

## Evaluation and scientific validity

During the 24-hour search, every candidate evaluation covers every official
validation file in the requested band. The evaluator reports that complete-band
metric separately from scientific eligibility. Validation inputs and truth are
inaccessible to the agent; only the resulting score, file vector, Health
evidence, and eligibility receipt are returned. All 20 labelled training files
remain a separate training split.

The evaluator reports the raw metric separately from scientific eligibility.
A finite raw score alone is **not** a valid result. A candidate is valid,
eligible for retention as a successful candidate, and selectable as a band or
final winner only when all three conditions hold:

1. its deliverables satisfy the frozen scoreability contract;
2. the raw score is finite; and
3. the evaluator obtains a PASS under the task-declared continuous-regression
   Health contract in
   `tasks/tidmad/framework_configs/health_regression.yaml`.

A Health FAIL, Health error, missing Health evidence, or indeterminate Health
result makes the candidate ineligible regardless of its raw score. The fixed
evaluator, not the agent, is the authority for this decision. It returns the
raw score, Health evidence, and eligibility separately.

Public reference rulers are provided for interpreting candidate results:

- `tasks/tidmad/reference_data/raw_and_ground_score.md` explains the common
  scoring ruler;
- `tasks/tidmad/reference_data/raw_baseline/` contains the raw-data floor;
- `tasks/tidmad/reference_data/ground_truth/` contains the perfect-denoiser
  reference ceiling, including per-file values;
- `tasks/tidmad/reference_data/official_paper_result/` contains published-model
  reference results.

These are evaluation requirements, not a prescribed experiment schedule.

For every candidate that you want evaluated, retain enough material to reload
and reproduce it: model source code, `weights.pth`, `architecture.json`,
`train_config.json`, and an exported TorchScript `model.pt`. The evaluator,
not candidate code, owns inference around that model. `model.pt` receives an
`int64` tensor of shape `[B, 40000]` containing raw ADC values shifted by +128,
and must return finite floating-point categorical logits of shape
`[B, 256, 40000]`. The evaluator applies `argmax` over the class dimension,
restores the persisted int8 representation, and creates the deliverable.

`weights.pth` must be a direct, non-empty PyTorch state dict whose tensors match
the state embedded in `model.pt`. This establishes that the submitted artifact
is a parameterized trained model; it does not prescribe an architecture.
`architecture.json` must include the fixed inference contract (and may include
additional architecture documentation):

```json
{
  "version": "tidmad-segment-model-v1",
  "segment_size": 40000,
  "input_dtype": "int64",
  "output_kind": "categorical_logits",
  "num_classes": 256,
  "inference_batch_size": 1
}
```

`inference_batch_size` may be from 1 through 32. Use `tidmad-score --help` for
the exact scoring interface. The evaluator snapshots the candidate, runs its
model on every validation file in the requested band, and retains every
candidate that obtains an eligible valid complete-band score. Retained bytes
cannot be replaced or removed from storage accounting. The highest eligible
complete-band score becomes that band's final winner.

The candidate scorer returns a finite higher-is-better scalar plus a 20-position
vector with one non-null entry for every file in the requested band. For
example, band `4-9` produces six non-null entries at positions 4 through 9:

```bash
tidmad-score \
  --band 0-3 \
  --candidate-id candidate-001 \
  --candidate-source /work/agent/candidates/candidate-001
```

There is no agent-callable final-scoring command. After the immutable deadline,
the evaluator stops the agent, takes the retained complete-band winner for each
band, replays each frozen trained model on the same authoritative full-band
validation scope, and composes the final 20-file score once. Before the
deadline, keep reproduction instructions and any additional explanation you
want preserved in each candidate directory. The evaluator's immutable retained
copies remain the authority for selection and finalization.

## Fixed resources

You have one NVIDIA H100, 16 vCPUs, about 200 GB RAM, outbound internet, and a
fixed 1 TiB scientific working-storage budget for this task.

The frozen task package, the provided training data, and all
scientific artifacts created during the run share this capacity. This includes
checkpoints, temporary files, caches, user-level environments, downloaded
packages and models, generated datasets, denoised outputs, logs, evaluation
products, candidate archives, and submission files.

The frozen task package and provided input data are read-only and must remain
present throughout the run. You are responsible for managing all other
storage within the fixed limit. Additional scientific working storage will not
be allocated during the evaluated run. You may delete, overwrite, compress, or
otherwise manage your intermediate artifacts as needed.

Every candidate that obtains an eligible valid score is retained locally by
the evaluator and continues to count against the 1 TiB limit for the remainder
of the run. An external durability backup does not remove or replace the local
retained copy and does not make that local capacity available again.

You must not use the boot/system filesystem, external or object storage,
network-mounted storage, or any location outside the provided scientific
working filesystem as additional working storage.

You may use the installed command-line tools and outbound public internet for
papers, documentation, public code, and package installation. Final model
artifacts must record enough dependency and source information for
reproduction. You have no
access to evaluator credentials, private validation targets, supervisor
controls, or external artifact storage; those are not mounted into the agent
environment.
