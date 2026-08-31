# Oxford-IIIT Pet task package

This package declares 37-way pet-breed classification over the official
Oxford-IIIT Pet dataset. It owns the scientific task independently of any one
training workflow or resource budget.

## Scientific contract

| Aspect | Declaration |
|---|---|
| Input | RGB JPEG decoded to float32 `[3, 144, 144]` by the task runtime |
| Target | integer breed class in `[0, 36]` |
| Objective | categorical cross entropy |
| Primary metric | accuracy, higher is better |
| Secondary metrics | macro-F1, higher; log loss, lower |
| Training identity | deterministic breed-stratified subset of the official train/validation list |
| Validation identity | deterministic disjoint remainder of the official train/validation list |
| Final identity | official test list, disjoint from training and validation |

The exact split derivation, source archives, checksums, and licensing notes are
recorded in `PROVENANCE.md`. Dataset bytes stay outside the repository.

## Package ownership

```text
composition.yaml                       static task binding
data/manifests/                        task-owned identities and integrity pins
declared/                              dataset, model I/O, metric, and Health declarations
plugins/                               model, metric, and Health implementations
runtime/pets_data_path.py              task-specific data and deliverable adapter
tools/                                 task-specific acquisition and manifest tools
expected/                              preserved task evidence fixtures
PROVENANCE.md                          dataset and derivation authority
STATUS.md                              supported capability record
```

This directory intentionally contains no experiment launcher, iteration count,
epoch count, data-exposure setting, literature-review treatment, output lock,
or VRAM budget. Those values vary across experiments and therefore belong
under `experiments/oxford_iiit_pet/`.

## Data preparation

Download and verify the official images with the task-owned tool:

```bash
python tasks/oxford_iiit_pet/tools/fetch_oxford_iiit_pet.py \
    --dest /path/to/oxford-iiit-pet --extract
```

The runtime consumes `/path/to/oxford-iiit-pet/images`. It selects identities
from the committed manifests rather than scanning the directory to invent a
split.

## Experiments

The bounded two-iteration infrastructure qualification is defined at:

```text
experiments/oxford_iiit_pet/two_iteration_qualification/
```

That experiment selects this unchanged task composition and supplies its own
workflow parameters. A new treatment must create a separate experiment
directory instead of editing this task package.

## Expected reference behavior

The preserved reference CNN is an intentionally weak witness. Its historical
chance-level collapse is retained as task Health evidence, not presented as a
competitive result. Scientific validity and infrastructure execution are
reported separately.
