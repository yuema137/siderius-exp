# Prepared scalar-regression arrays

This consumer adapter reads frozen scientific data through the existing
TaskDataPath contract. SIDERIUS source requires no task-name branches.

## Physical layout

```text
manifest.json
training/inputs.npy                    float32 [N_train, C, L]
training/targets.npy                   float32 [N_train, 1]
evaluator/validation/inputs.npy        float32 [N_val, C, L]
evaluator/validation/targets.npy       float32 [N_val, 1]
evaluator/validation/loss_indices.npy  int64 [N_val / 10]
```

Arrays are external read-only files. Conversion, preprocessing, finite-value
checks and full SHA-256 checks happen before deployment. Runtime memory maps
the arrays; it does not parse raw HDF5 or reprocess all inputs each epoch.
It checks the pinned manifest digest and array shape/dtype. Runtime metadata
checking is not a replacement for deployment's full-file checksum verification.

The composition's `declaration_path` reference pins counts, dimensions, manifest
SHA-256 and exact loss row identities. Serialized scopes contain the declaration
digest, split, population count and optional subset indices, never truth values.
Full scopes use a compact range. Test is not a representable split.

## Selection and scoring

The training pool is the full released training split. `portion` selects a
scope, and `EpochSamplingParams.train_portion` selects per-epoch exposure
inside that scope. Different epoch seeds can draw different rows. Neither
choice changes the available pool. One partition, ID 0, represents each array;
undeclared partitions and subset-reference vocabularies are rejected.

Validation selection is fixed across planner seeds. At `portion=0.1` it is
exactly the declared loss subset; at `portion=1` it is the whole validation
population. Other fractions are stable nested draws for Trial/qualification.
The experiment supplies `training_validation_portion=0.1` and
`formal_eval_portion=1`; the adapter does not confuse a Formal epoch-loss scope
with the full Formal scoring scope.

Model outputs must be one scalar per input in physical units. If training
normalizes targets, the exported model must invert that normalization. JSON
deliverables reject non-finite values, duplicate row keys, wrong declaration
identity and malformed scalar outputs. Metrics reject missing or extra rows
and compute global RMSE/R2, never averages of per-batch scores. R2 with zero
target variance is explicitly undefined. Health has an explicit `none`
binding: no uncalibrated task-specific threshold is introduced. Scoreability
and exact population checks remain mandatory.

## Access and qualification boundaries

The adapter is not a security sandbox. `validation_dataset` is a trusted
materialization interface used by the native validation/inference core.
Private target access needs a qualified execution/deployment boundary; Unix
mode bits alone do not isolate generated code running under the evaluator's
account. The operator-owned tiny native smoke proves subprocess transport,
training, epoch loss, export/restore, inference, and independent score parity.
It does not prove private-worker isolation or autonomous agent iterations.

No source clean signal, separate noise, auxiliary truth parameters, raw files,
or test arrays are needed in the prepared runtime view. Provenance stays in
the external manifest; row IDs never enter model features.
