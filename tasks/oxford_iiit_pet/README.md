# Oxford-IIIT Pet task package

This package declares 37-way pet-breed classification over the official
Oxford-IIIT Pet dataset. It owns the scientific task independently of any one
training workflow or resource budget.

## Start with the tutorial

Follow the [Pet notebook and setup guide](../../tutorials/supplementary/pet/README.md)
to prepare data, create an external project, change parameters and run a
three-iteration demo through its saved script. The guide includes a recorded
example and explains where your own results appear. This is a process demo,
not a paper artifact or a promise of a high score.

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
compositions/bounded_qualification.yaml  reusable bounded task binding
data/manifests/                        task-owned identities and integrity pins
declared/                              dataset, model I/O, metric, and Health declarations
plugins/                               model, metric, and Health implementations
runtime/pets_data_path.py              task-specific data and deliverable adapter
tools/                                 task-specific acquisition and manifest tools
expected/                              preserved task evidence fixtures
PROVENANCE.md                          dataset and derivation authority
STATUS.md                              supported capability record
```

The bounded composition defines a reusable 370-row training and 74-row
validation scope. It does not decide that a run must use that scope; an
experiment selects it explicitly.

This directory intentionally contains no experiment launcher, iteration count,
epoch count, data-exposure setting, literature-review treatment, output lock,
or VRAM budget. Those values vary across experiments and therefore belong
under `experiments/oxford_iiit_pet/`.

## Data preparation

From the `siderius-exp` repository root, after `uv sync --group dev --frozen`,
download, verify and extract the official images and annotations. Replace the
destination with a directory outside both source repositories:

```bash
.venv/bin/python -m tasks.oxford_iiit_pet.tools.fetch_oxford_iiit_pet \
    --dest /path/to/external/oxford-iiit-pet --extract
```

The tool prints `[verified]` for each archive and creates `images/` and
`annotations/` under the destination. Existing archives are verified rather
than downloaded again. Pass `/path/to/external/oxford-iiit-pet/images` as the
experiment's `data_dir`; the runtime selects images from the committed manifests.
See [data preparation details](data/README.md) for offline verification and
manifest ownership.

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
