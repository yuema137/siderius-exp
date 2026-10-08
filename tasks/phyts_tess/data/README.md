# PhyTS TESS data

Raw datasets are never committed. This directory holds the committed
**identity manifest** and the instructions for staging a run data root.

## What is committed

`manifests/rotation_identity.csv` — 3,780 rows, one per light curve, columns
`split, gaia_id, tic, sector, frot, frot_err`.

It is the **split authority**. Scope construction reads it rather than the
staged data, for two reasons: `ScopeBuildRequest` carries no physical data
root, and pinning the population in Git means a run's split cannot drift with
whatever happens to sit in `--data_dir`.

| split | curves | stars |
|---|---|---|
| `train` | 3,338 | 505 |
| `val` | 442 | 64 |

The manifest's source and verification record are in [PROVENANCE.md](../PROVENANCE.md).

The held-out **test** population (403 curves, 64 stars) has **no row and no
target here**. Its targets are not committed anywhere in this repository.

## Staging a run data root

```bash
uv sync --group dev --group tutorial --frozen
.venv/bin/python tasks/phyts_tess/tools/stage_data.py \
    --source /path/to/PhyTS/TESS/split \
    --data_dir /path/to/run-data
```

`--source` is the directory holding the released
`tess_regression_{train,val,test}.parquet` files. The tool copies **two**
files by name — never a glob — converts them to `tess_rotation_{split}.npz`,
and verifies that the resulting population matches the committed manifest
exactly, refusing on any mismatch.

Run these commands from this exp checkout. The frozen `tutorial` dependency
group supplies pyarrow for Parquet conversion; the staged NPZ run inputs do not
require Parquet decoding. Staging and later commands use this checkout's own
`.venv/bin/python`.

Expected output: roughly 15 MiB for train and 2 MiB for val.

## Why the test split is handled this way

Two mechanisms, and **neither alone is sufficient**.

1. **Declaration.** `TessSplit` admits `train` and `val` only, the committed
   manifest carries no test row, and scope deserialization refuses a payload
   naming `test`. No scope this task can construct reaches the held-out
   population.
2. **Filesystem.** A declaration says nothing about a file that happens to
   sit in the same directory, which agent-generated code could simply open.
   The staging tool therefore refuses to write into a destination that
   already contains anything matching `test`, and copies only the two named
   splits.

Keep the released parquet directory — which does contain the test split —
outside every run's `--data_dir`. A final evaluation against the held-out
population is a separate, manual step against that separate path, performed
after a campaign ends and never by the agent loop.
