# Tasks

For your first run, use the [tutorial index](../tutorials/README.md): it shows
which tasks have a notebook and a step-by-step setup guide. This directory is
the reference for the scientific task definitions behind those examples.

Choose a package below to understand its prediction problem, data and scoring.
**Every task starts with its README.** That page links to the task's exact
configuration and any technical references, such as `STATUS.md` for supported
capabilities or `PROVENANCE.md` for data identity and evidence. Those reference
files are not present in every package.

| Task | Purpose | Start here |
|---|---|---|
| [`tidmad`](tidmad/) | time-series denoising | [`README.md`](tidmad/README.md) |
| [`supernemo_signal_background`](supernemo_signal_background/) | event classification | [`README.md`](supernemo_signal_background/README.md) |
| [`majorana_low_avse`](majorana_low_avse/) | waveform classification | [`README.md`](majorana_low_avse/README.md) |
| [`oxford_iiit_pet`](oxford_iiit_pet/) | pet-breed classification | [`README.md`](oxford_iiit_pet/README.md) |
| [`davis_future_prediction`](davis_future_prediction/) | video-frame prediction | [`README.md`](davis_future_prediction/README.md) |
| [`cancer_gene_identification`](cancer_gene_identification/) | cancer-gene ranking | [`README.md`](cancer_gene_identification/README.md) |
| [`phyts_tess`](phyts_tess/) | stellar rotation regression | [`README.md`](phyts_tess/README.md) |
| [`phyts_ligo`](phyts_ligo/) | chirp-mass regression | [`README.md`](phyts_ligo/README.md) |
| [`phyts_project8`](phyts_project8/) | electron-energy regression | [`README.md`](phyts_project8/README.md) |

## Why is there also a shared directory?

[`shared/`](shared/README.md) contains reusable code used by several tasks, such
as reading prepared arrays, calculating regression metrics and verifying data
archives. It is **not another scientific task** and has no standalone experiment
to run. Its README explains which tasks use it and links to the detailed contract.

## What belongs in a task?

Each task directory is a static scientific task package consumed through SIDERIUS
task-composition and plugin contracts. Task packages own dataset identity and
splits, scientific semantics, model I/O, objectives, metrics, Health
definitions, plugins, runtime adapters, and task provenance.

Task packages do not own iteration schedules, resource budgets, training
exposure, literature-review treatments, or result records. Experiments select
a workflow and supply those treatment values; the workflow retains ownership
of Trial/Formal mechanics. Multi-run selection and authorization belong under
`campaigns/`.

Private datasets and credentials are never committed.
