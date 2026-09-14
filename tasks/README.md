# Tasks

Start here when you need to understand a scientific problem and its immutable
task-owned inputs. Choose a package below; its `STATUS.md` describes capability
and its `PROVENANCE.md` describes data identity and historical evidence. A task
README explains the contract at a human level and links to the exact files.

| Task | Purpose | Current entrypoint |
|---|---|---|
| [`tidmad`](tidmad/) | time-series denoising | [`STATUS.md`](tidmad/STATUS.md) |
| [`supernemo_signal_background`](supernemo_signal_background/) | event classification | [`README.md`](supernemo_signal_background/README.md) |
| [`majorana_low_avse`](majorana_low_avse/) | waveform classification | [`README.md`](majorana_low_avse/README.md) |
| [`oxford_iiit_pet`](oxford_iiit_pet/) | pet-breed classification | [`STATUS.md`](oxford_iiit_pet/STATUS.md) |
| [`davis_future_prediction`](davis_future_prediction/) | video-frame prediction | [`STATUS.md`](davis_future_prediction/STATUS.md) |
| [`cancer_gene_identification`](cancer_gene_identification/) | cancer-gene ranking | [`STATUS.md`](cancer_gene_identification/STATUS.md) |

Each directory is a static scientific task package consumed through SIDERIUS
task-composition and plugin contracts. Task packages own dataset identity and
splits, scientific semantics, model I/O, objectives, metrics, Health
definitions, plugins, runtime adapters, and task provenance.

Task packages do not own iteration schedules, resource budgets, training
exposure, literature-review treatments, or result records. Experiments select
a workflow and supply those treatment values; the workflow retains ownership
of Trial/Formal mechanics. Multi-run selection and authorization belong under
`campaigns/`.

Private datasets and credentials are never committed.
