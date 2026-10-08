# DAVIS data: keep videos outside the repository

This directory contains the task's committed sequence/clip manifests and decode
probes, not video files. Cloning the repository downloads no dataset. The task
reads RGB frames from the official DAVIS 2017 TrainVal 480p archive; segmentation
annotations in that archive are not used.

## Reuse an existing copy

Set `DAVIS_DATA` to the directory containing both the archive and its extracted
`DAVIS/` tree. Run from your installed exp checkout:

```bash
export DAVIS_DATA="/absolute/path/DAVIS_2017"
.venv/bin/python -m tasks.davis_future_prediction.tools.fetch_davis \
  --dest "$DAVIS_DATA" --no-download --check-layout
```

This verifies the archive hash and checks the 90 committed sequence directories
contain JPEGs. It does not download or modify your frames. A layout check alone
does not verify every frame's contents or prove all task windows decode.

## Acquire it on a new machine

The [official source](https://davischallenge.org/davis2017/code.html) links the
832,766,765-byte archive (about 0.833 GB). Keep extra disk space for extraction,
environments and run outputs. If you do not already have it:

```bash
.venv/bin/python -m tasks.davis_future_prediction.tools.fetch_davis \
  --dest "$DAVIS_DATA" --extract --check-layout
```

The helper verifies SHA-256 before extraction and refuses a destination inside
the exp repository. It reuses a present archive; `--no-download` makes accidental
network fetching an error. Existing extracted directories are not overwritten.
Consult the recorded [source and data terms](../PROVENANCE.md) before reuse.

Expected layout:

```text
DAVIS_DATA/
  DAVIS-2017-trainval-480p.zip
  DAVIS/JPEGImages/480p/<sequence_name>/00000.jpg
```

## Understand the original manifests

| File | What it declares |
|---|---|
| `manifests/sequences.csv` | 90 sequence identities: 60 Train / 15 Validation / 15 Final |
| `manifests/clips.csv` | 600 fixed windows across those disjoint roles |
| `manifests/gate2_train.csv` | First window of each of 60 Train sequences |
| `manifests/gate2_validation.csv` | First window of each of 15 Validation sequences |
| `manifests/gate2_final.csv` | First window of each of 15 reserved Final sequences |
| `manifests/execution.json` | Frozen decoder settings and ten decoded-window hashes |
| `manifests/SHA256SUMS` | Manifest integrity pins |

Each window has eight RGB context frames and four future target frames, resized
to 128×224 and scaled to [0,1] by the task-owned
[runtime decoder](../runtime/davis_data_path.py). Sequences never cross roles.
The [tutorial](../../../tutorials/supplementary/davis/README.md) uses the bounded
Train/Validation manifests, leaves Final unused and verifies required frames
before launch. Do not regenerate or reshuffle manifests as a setup step.
