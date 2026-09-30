# PhyTS TESS — orchestrated research condition

You have six hours on one NVIDIA RTX 5090, with an 8 GiB VRAM budget per
training attempt, to obtain the strongest **scientifically valid**
near-core rotation-frequency regressor you can for the PhyTS TESS task.
Work autonomously for the full budget. At the start of every invocation,
inspect the existing files and results in your workspace and continue from
them instead of starting over.

The clock starts when the supervisor launches this evaluated run. A process
exit or restart does not reset or extend it. Environment and data
preparation completed before that launch is outside the six-hour window.

## What you have

The concrete paths are in `SIDERIUS-RUN.md` beside this file; this page
says what each thing is.

- **The task package, agent view.** The frozen PhyTS TESS task definition:
  `declared/task_config.yaml` (the task description and the forward
  contract), `declared/dataset_profile.json`, `declared/metric_r2.json`,
  `declared/task_health.yaml`, `declared/reference_baselines.json`, the
  public data-path implementation, the scoreability contract, and one
  reference plugin. Evaluator-only assets — the scoring arithmetic, the
  identity manifest with validation targets, and the secondary-metric
  declarations — are intentionally absent.
- **The training split with targets** and **the validation split without
  targets**: 3,338 training curves and 442 validation curves, as staged
  `.npz` archives of raw flux keyed by `gaia_id:sector`, plus manifests of
  identities. Validation targets are held by the evaluator.
- **`tess-score`**: the complete-split candidate-scoring entry point,
  invoked through the fixed sudo route the run declaration names.
- **A writable workspace** for your own code, requests, outputs and
  candidates.
- **The SIDERIUS toolkit**, installed at a pinned revision with its own
  Python environment, and the published public runtime modules that bind
  the evaluator into your process.

Read the frozen task package before designing models. Its
`task_description` carries the published reference points and the known
discrepancies between the benchmark paper and its code; they describe the
task and are not a recommendation.

The original scientific reference is PhyTS, *A Benchmark for Scientific
Time Series*, TESS subset, Task B. The task package's `PROVENANCE.md`
records the data source and the upstream pipelines.

## Scientific objective

Predict `frot`, a pulsating star's near-core rotation frequency in cycles
per day, from a single TESS light curve. Higher R-squared over the complete
validation split is better among candidates that pass the validity
contract below. R-squared is normalized by the evaluation set's own
variance: a model that predicts the mean scores exactly `0.0`, and a
negative value is real information, not an error.

The evaluated solution must be a trained ML regressor fitted from the
provided labelled training data. Its only inference input is the
evaluator-provided batch of curves in the frozen forward contract:
`[B, 1, 1024]` float32, each curve already z-scored over its own observed
samples and right-padded with its last observed value; the output must be
`[B, 1]` float32, unbounded. Normalization, padding, batching and
deliverable writing are fixed evaluator operations; candidate-specific
preprocessing or postprocessing outside the submitted model is not part of
this task.

You may inspect training targets and use them to fit, validate and diagnose
a model. The submitted predictor must infer each curve's frequency from that
curve. A lookup keyed on identity, call order or any persistent state that
reconstructs which validation curve is being scored is not an eligible
trained model, even when stored as parameters or buffers. This restriction
does not prohibit learned weights derived from ordinary supervised training.

Validation targets are not part of the information available to this
condition. The evaluator owns them and supplies your frozen model with
curves only. It enforces that boundary through file ownership and the
scoring interface.

## Evaluation and scientific validity

Every candidate evaluation covers the complete validation split. The
evaluator reports the raw metric separately from scientific eligibility. A
finite raw score alone is **not** a valid result. A candidate is valid,
retained, and selectable as the run's winner only when all three hold:

1. its deliverable satisfies the frozen scoreability contract
   (`tasks/phyts_tess/runtime/scoreability.py`);
2. the raw R-squared is finite; and
3. the evaluator obtains a PASS under the task-declared Health family in
   `tasks/phyts_tess/declared/task_health.yaml`.

A Health FAIL, Health error, or indeterminate Health result makes the
candidate ineligible regardless of its raw score. The fixed evaluator, not
you, is the authority for this decision, and it returns the raw score, the
observational RMSE and MAE, the Health evidence and eligibility separately.
Note that the task's one declared Health check is currently `recording`:
it is measured and reported, and a candidate that trips it is still
eligible. Final scientific acceptance includes review of the submitted
model and training artifacts against the trained-model rule above.

## Candidate contract

For every candidate you want evaluated, retain enough material to reload
and reproduce it. The published exporter,
`experiments.phyts_tess.main_orchestrator.tess_evaluation.TessNativeExporter`,
writes the complete package from a native tuner result; a hand-built
candidate must carry the same files:

| file | meaning |
|---|---|
| `model.pt` | TorchScript, self-contained; `[B, 1, 1024]` float32 in, one scalar per curve out |
| `weights.pth` | a direct, non-empty state dict whose tensors match the state inside `model.pt` |
| `contract.json` | the fixed inference contract below |
| `native_reconstruction.json`, `train_config.json` | what produced it: configuration, checkpoint and source hashes, `model_type` |
| `model/` | retained source, for diagnosis; the evaluator never imports it |

```json
{
  "version": "phyts-tess-rotation-model-v1",
  "sequence_length": 1024,
  "input_dtype": "float32",
  "output_kind": "continuous_scalar",
  "inference_batch_size": 64
}
```

`inference_batch_size` may be from 1 through 256. A candidate must contain
no symlinks and no data files. The evaluator snapshots the candidate, runs
its model over the complete validation split on its own side, and retains
every evaluated candidate together with its receipt; retained bytes are not
removed for the rest of the run.

The scoring interface, invoked for you by the bound evaluator
(`SUBMISSION.md` in the public runtime shows the binding):

```bash
sudo -n -u tess-coordinator /usr/local/sbin/tess-score \
  --candidate-source /var/lib/tess-candidates/<run>/<candidate-id> \
  --candidate-id <candidate-id> \
  --run-id <run>
```

It prints one path: the receipt, readable by you and writable by nobody
after publication. `tess_receipt.read_tess_evaluation` reads it bound to
the exact candidate bytes, run and invocation. A successful tuner result is
not a scoring receipt; only the receipt is.

There is no agent-callable final-scoring command. After the deadline the
operator takes the eligible candidate with the highest receipt R-squared as
the run's result. Before the deadline, keep reproduction instructions and
any explanation you want preserved in each candidate directory.

## Fixed resources

One RTX 5090 (about 31.8 GiB; the 8 GiB budget is a budget, not the
capacity), the host's CPUs and RAM, outbound internet for provider calls
only, and the writable workspace. The task package and the staged data are
read-only and remain present throughout the run. Checkpoints, caches,
generated code, candidates, diagnostics and logs are yours to manage inside
the workspace. You have no access to evaluator credentials, validation
targets, the coordinator's state directory, or supervisor controls.
