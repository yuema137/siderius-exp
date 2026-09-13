# `data/` — TIDMAD data root (nothing is stored here)

No dataset lives in this directory, and nothing in this pack downloads one
(roadmap §22.23.10). The TIDMAD HDF5 files are acquired from the official
distribution named in `../PROVENANCE.md` into a **machine-local**, read-only
directory. Every experiment or campaign names that directory explicitly:

```bash
--data_dir /path/to/TIDMAD
```

The campaign preflight and chain launcher validate the directory before any
run spends compute. Which files exist and how they are named is projected
read-only in `../resolved/identity.json`.

That is what the qualification experiment launcher requires, and it is why the
command published in `../README.md` reproduces on any machine: the caller
selects its own data root instead of depending on framework state.

Prepared/derived data, caches and run artifacts belong to the workspace
(`--workspace`, default `./siderius_workspace`, gitignored) — never to the
tracked example tree.

## Stage the approved anchor

The composed metric (`runtime/scoring.py::_task_owned_score_kwargs`) and Trial
adapter (`runtime/tidmad_data_path.py::trial_anchor_path`) both select
`data_dir/segment_anchors.json`. They do not automatically use the copy shipped
in this task. Stage it during data-root preparation, before making that root
read-only, and verify the bytes again before an affected fresh run.

From the exact siderius-exp checkout, with the explicit prepared data root:

```bash
set -euo pipefail
tidmad_data_dir=/path/to/prepared/TIDMAD
tidmad_anchor=tasks/tidmad/reference_data/segment_anchors.json
test -d "$tidmad_data_dir"
if [[ ! -e "$tidmad_data_dir/segment_anchors.json" && ! -L "$tidmad_data_dir/segment_anchors.json" ]]; then
    cp --no-clobber -- "$tidmad_anchor" "$tidmad_data_dir/segment_anchors.json"
fi
cmp -- "$tidmad_anchor" "$tidmad_data_dir/segment_anchors.json"
sha256sum -- "$tidmad_anchor" "$tidmad_data_dir/segment_anchors.json"
```

Both hashes must be
`0c44b6084dc8afc4dc2fa34f5253bc8d780b4e8ae086945e7051d8bf7928ba90`.
If comparison fails, stop and resolve which input was selected; do not overwrite
an existing ruler, regenerate anchors, or recalibrate to make a run proceed.
The command copies only the approved committed anchor when absent, never HDF5
data. Record the comparison and both hashes with the fresh run's provenance.

The campaign preflight checks anchor presence, not this byte equality. Gold
pooled Stage3 uses the committed anchor via `campaigns/tidmad_gold/paths.py`;
that separate reader does not certify the composed metric's staged input.
No real-data directory or historical workspace is changed by these instructions
until an operator explicitly performs the staging step.
