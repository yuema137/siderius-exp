# `data/` — TIDMAD data root (nothing is stored here)

No dataset lives in this directory. Prepare the official HDF5 files in an
external data directory using the [one-band tutorial's download and preparation steps](../../../tutorials/paper/tidmad/README.md#download-your-band-data).
[Provenance](../PROVENANCE.md) identifies the official distribution. Each
experiment or campaign selects its data root explicitly with `--data_dir`.

The bound [dataset profile](../resolved/dataset_profile.json) declares file
patterns and topology; `resolved/identity.json` is an imported reference snapshot.
The selected launcher owns data preflight. Use the [experiment guide](../../../experiments/tidmad/main_fixed_workflow/README.md)
for the fixed workflow's band and input checks, or the tutorial above for
its separate file-holdout route. Prepare the anchor before making the data root
read-only. Keep derived data, caches and run artifacts outside both repositories.

## Stage the approved anchor

The run needs `segment_anchors.json` in its data directory as a scoring
reference. Copy the approved file during data preparation, before making that
directory read-only. The command below copies it only when absent, then checks
that the selected file exactly matches the approved copy. Run the check again
before a fresh run.

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
```

Success returns without an error; `cmp` prints nothing when the files match.
If comparison fails, stop and check which data directory was selected. Do not
overwrite an existing scoring reference, regenerate anchors or recalibrate to
make a run proceed. This command copies no HDF5 data.

See the [staging contract](staging.md) for reader ownership, exact reference
identity and the different preflight checks. Existing data and historical
workspaces are unchanged until you explicitly run the staging command.
