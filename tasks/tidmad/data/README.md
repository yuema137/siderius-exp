# `data/` — TIDMAD data root (nothing is stored here)

No dataset lives in this directory. Prepare the official HDF5 files in an
external data directory using the [one-band tutorial's reuse or download steps](../../../tutorials/paper/tidmad/README.md#choose-existing-data-or-a-download).
[Provenance](../PROVENANCE.md) identifies the official distribution. Each
experiment or campaign selects its data root explicitly with `--data_dir`.

The bound [dataset profile](../resolved/dataset_profile.json) declares file
patterns and topology; `resolved/identity.json` is an imported reference snapshot.
The selected launcher owns data preflight. Use the [experiment guide](../../../experiments/tidmad/main_fixed_workflow/README.md)
for the fixed workflow's band/checksum requirements, or the tutorial above for
its separate file-holdout route. Prepare the anchor before making the data root
read-only. Keep derived data, caches and run artifacts outside both repositories.

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
