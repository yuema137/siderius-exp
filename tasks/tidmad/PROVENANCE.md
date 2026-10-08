# Provenance — `tidmad`

## Data source

- **Dataset / paper**: *TIDMAD: Time Series Dataset for Discovering Dark
  Matter with AI Denoising* — J. T. Fry, X. H. Fu, Z. Fu, K. M. W. Pappas,
  L. Winslow, A. Li. arXiv: <https://arxiv.org/abs/2406.04378>.
- **Official distribution**: the paper's repository
  <https://github.com/jessicafry/TIDMAD> (its `download_data.py` /
  `filelist.dat` retrieve the HDF5 files from the OSDF caches). The repository
  states that both the TIDMAD dataset and the associated software are licensed
  under **CC BY 4.0** (verified 2026-08-15 from the repository README; consult
  the source for the authoritative current terms).
- **Files SIDERIUS reads**: `abra_training_{file_index:04d}.h5` and
  `abra_validation_{file_index:04d}.h5`, `file_index` 0–19 (see
  the bound `resolved/dataset_profile.json`; `resolved/identity.json` preserves
  the imported file-family/index snapshot).

Raw data is never committed to this repository. The
historical `examples/tidmad/` projection did not fetch it; current task data is
caller-staged outside this repository.

## Literature-review configuration

`framework_configs/lit_review.yaml` is the current task-owned literature
configuration. Its historical source was SIDERIUS
`98610b8d:configs/lit_review_config.yaml`, not the active framework pin or the
current task file. Those historical source bytes have SHA-256
`004ffa44c7bfd3684c6e07c63091dabf6d059050309934fd3862577baaaae203`.
The projection preserves every executable value while removing repository-
internal historical commentary; task-specific root papers and confidence
criteria therefore no longer live in framework infra.

## Machine-local data root (reference, no path recorded here)

Every launcher selects the machine-local, read-only data directory explicitly
with `--data_dir`. The launcher validates it before any spend; neither the
framework checkout nor repository-local configuration selects a task path.

## Frozen reference artifacts (already tracked under `reference_data/`)

| artifact | path | role |
|---|---|---|
| segment anchor map | `reference_data/segment_anchors.json` | scoring normalisation (`s_max` per anchor) |
| raw baseline | `reference_data/raw_baseline/` | metric floor (no denoising) |
| ground truth | `reference_data/ground_truth/` | metric ceiling |
| official paper-model scores | `reference_data/official_paper_result/README.md` | paper comparability |
| paper-spec baseline configs | `reference_data/legacy_baseline_configs.json` | paper-aligned hyperparameters |
| signal frequencies | `reference_data/tidmad_signal_frequencies.txt` | injected-signal reference |

## Snapshots in `resolved/` — provenance

These files were generated at PR0 (2026-08-15) by the then-current
`tools/example_packs/projection.py`. The original
`tests/unit/examples/test_tidmad_projection.py` deep-compared them with the
production authorities at that checkpoint. Those tool/test paths describe
historical provenance, not a current regeneration command.

Current compositions consume task-owned declarations as described in
[the resolved-file guide](resolved/README.md) and [the task contract](task-contract.md).
The imported source locations explain their origin; they are not competing
framework-side scientific owners. Preserve historical snapshots and archived
identities when defining and qualifying a changed task.
