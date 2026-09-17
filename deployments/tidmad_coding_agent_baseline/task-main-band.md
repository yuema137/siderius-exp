# TIDMAD single-band coding-agent baseline

You have one NVIDIA H100 and 24 hours of wall-clock time to develop a trained
machine-learning denoiser for TIDMAD band `{{BAND}}`. This run concerns **only
that band**. Inspect your existing workspace at the start of every invocation
and continue from it; a CLI or machine restart does not reset the deadline.

## Scientific task and supplied material

The labelled training files under `/data/public-training/` contain noisy
detector time series paired with clean targets. The read-only task package at
`/work/input/tasks/tidmad/` states the data, model-I/O, scoring, scoreability,
and Health contracts, and includes public scientific references. The original
dataset paper is Fry et al., *TIDMAD: Time Series Dataset for Discovering Dark
Matter with AI Denoising*, arXiv:2406.04378. Read the task package before
building a model.

The active task declaration for this run is
`/work/input/tasks/tidmad/compositions/continuous_regression_frozen_pool.yaml`,
which binds `declared/task_config_regression.yaml` and
`framework_configs/health_regression.yaml`. The package also retains historical
classification material, including `resolved/model_io_contract.json` with a
256-class output. That snapshot is **not** this run's model interface. The
continuous-regression interface stated below and enforced by `tidmad-score`
is the submission contract for this run.

For this main single-band condition, each public training file contains only
the same fixed 20 of its original 200 PSD segments selected in
`/work/input/tasks/tidmad/declared/frozen_training_pool_v1.json`. The public
file packs those segments consecutively; its local segment positions 0–19 are
not the original positions. This is the complete permitted fitting pool for
the band. You may choose smaller Trial samples from it, but every fitted
candidate must use training examples only from this pool. Validation scoring
still uses every validation file in the band at full scope.

Your result must be a trained ML model that maps each evaluator-provided raw,
non-overlapping segment to a cleaned waveform. The evaluator supplies the
segment as an `int64` tensor of shape `[B, 40000]`, with raw ADC values shifted
by +128. Your model must return finite continuous floating-point predictions
of shape `[B, 40000]` in the same offset domain. The evaluator alone converts
the output to the task's persisted ABRA format, reconstructs files, and scores
them. Do not submit 256-class logits or per-file outputs. One frozen model
artifact must be used for **every validation file in band `{{BAND}}`**.

Clean training targets may be used for supervised fitting and diagnostics.
A deterministic per-file or absolute-time lookup, frequency schedule, waveform
template, or target-derived recipe used instead of raw-to-clean ML inference
is not a trained denoising model. Architecture and fitting choices are yours.

The only optional human advice is `/work/input/advice.json` when the frozen
`/work/input/treatment.json` explicitly enables it. For this no-advice
condition, that file is absent. No historical campaign workspace or previous
agent trajectory is supplied.

## Evaluation

Run `tidmad-score --help` to see the candidate-submission interface. For
example, submit one complete candidate with:

```bash
tidmad-score candidate --band {{BAND}} \
  --candidate-id example-1 --candidate-source /work/agent/example-1
```

The evaluator scores **every validation file in band `{{BAND}}`**, not a single
development anchor. Training and validation files are disjoint. You may use
validation feedback repeatedly during development; it is not a hidden test.
Only a scoreable, finite result with a PASS under the task-declared continuous-
regression Health checks is eligible to become a band winner. The receipt
reports metric, file vector, Health evidence, and eligibility separately.
An eligible automatic receipt does not itself prove that genuine ML training
occurred; submitted code and fitting evidence remain subject to offline
scientific review.

Keep each scored candidate's `model.py` (or `model/`), `weights.pth`,
`architecture.json`, `train_config.json`, and exported TorchScript `model.pt`.
The state dict in `weights.pth` must match the parameters in `model.pt`. The
regression architecture contract is:

```json
{
  "version": "tidmad-segment-model-v2",
  "segment_size": 40000,
  "input_dtype": "int64",
  "output_kind": "continuous_regression",
  "inference_batch_size": 1
}
```

`inference_batch_size` may be 1–32. Every eligible scored candidate is
retained by the evaluator on the local fixed working disk; an external backup
does not free that local capacity. At the deadline the evaluator freezes and
replays the best retained candidate for this band, then packages its code,
weights, configuration, score vector, and provenance. No denoised HDF5 files
need to be kept as final deliverables. Leave reproduction instructions in
your workspace.

## Resources and boundaries

The 24-hour clock starts at official launch and survives invocations and
restarts. You have one H100, 16 vCPUs, about 200 GB RAM, outbound internet,
and a fixed 500 GiB scientific working filesystem. The frozen inputs and task
package, environments, caches, checkpoints, temporary data, logs, retained
candidates, and outputs all share that capacity. Frozen inputs are read-only.
You may manage your own intermediate files, but no additional scientific
storage will be allocated; boot/system storage, object storage, network mounts,
and external storage are not overflow working space. Write scientific state
under `/work/agent/` or the other supplied working-filesystem paths only.
