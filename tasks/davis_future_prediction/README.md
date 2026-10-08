# DAVIS future-frame prediction task package

This package declares continuous future-frame prediction over DAVIS 2017. It
owns the scientific task independently of any experiment, campaign, or
Trial/Formal workflow configuration.

## Scientific contract

| Aspect | Declaration |
|---|---|
| Input | eight RGB context frames as float32 `[3, 8, 128, 224]` |
| Target | next four RGB frames as float32 `[3, 4, 128, 224]` |
| Objective | exact L1 through the task-owned `davis_exact_l1` plugin |
| Primary metric | global MSE, lower is better |
| Secondary metrics | PSNR, higher; MAE, lower |
| Split authority | deterministic sequence-level train, validation, and final identities |
| Clip authority | deterministic `(sequence_name, start_frame)` windows |

The source archive, sequence derivation, clip generation, checksums, and
licensing evidence are recorded in `PROVENANCE.md`. Dataset bytes remain
outside the repository.

## Package ownership

```text
compositions/bounded_qualification.yaml  reusable 60/15 clip binding
data/manifests/                          sequence and clip identities with pins
declared/                                dataset, model I/O, metric, and Health declarations
plugins/                                 objective, model, metric, and Health implementations
runtime/davis_data_path.py               task-specific data and deliverable adapter
tools/                                   task-specific acquisition and manifest tools
expected/                                preserved task evidence fixtures
PROVENANCE.md                            dataset and derivation authority
STATUS.md                                supported capability record
```

The bounded composition defines a reusable 60-clip training and 15-clip
validation scope. It does not decide that a run must use that scope; an
experiment selects it explicitly.

This directory intentionally contains no experiment launcher, iteration or
epoch count, resource budget, literature-review treatment, or output lock.
Trial/Formal behavior belongs to the selected workflow, while the experiment
supplies approved values for that workflow.

## Data preparation

Use the task-owned acquisition tool:

```bash
.venv/bin/python tasks/davis_future_prediction/tools/fetch_davis.py \
    --dest /path/to/davis-root --extract
```

The runtime expects `/path/to/davis-root/DAVIS/JPEGImages/480p` and selects
windows from committed manifests rather than inventing a split from the
directory contents.

## Experiments

The bounded two-iteration infrastructure qualification is defined at:

```text
experiments/davis_future_prediction/two_iteration_qualification/
```

A new treatment creates a separate experiment identity instead of modifying
this task package.

## Result interpretation

Qualification scores prove execution and lower-is-better ordering. They are
not automatically competitive scientific results. Infrastructure validity,
Health validity, and scientific quality remain separate claims.
