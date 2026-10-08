# Oxford-IIIT Pet data preparation

This directory stores image identities and verification records. Dataset
archives and extracted files stay outside both the `siderius-exp` and
`SIDERIUS` repositories.
Cloning this repository does not download the dataset.

## Acquire or verify the data

1. From the `siderius-exp` repository root, prepare its environment with
   `uv sync --group dev --frozen`.
2. Choose an external destination and run the task-owned acquisition tool:

   ```bash
   .venv/bin/python -m tasks.oxford_iiit_pet.tools.fetch_oxford_iiit_pet \
       --dest /path/to/external/oxford-iiit-pet --extract
   ```

   Missing archives are downloaded from the official Oxford source: about
   792 MB of images and 19 MB of annotations. Each archive is verified
   against the approved source before extraction. Success prints `[verified]` for
   both archives and leaves `images/` and `annotations/` under the destination.
   An existing extraction directory is skipped.
3. Pass `/path/to/external/oxford-iiit-pet/images` as the experiment's `data_dir`.
   The runtime reads the images named in the selected committed manifests;
   acquisition does not regenerate or change those manifests.

Existing archives are verified rather than downloaded again. If verification
fails, stop and inspect the error; use a fresh external destination if you need
to acquire another copy from the official source. To verify local archives
without allowing any download, run:

```bash
.venv/bin/python -m tasks.oxford_iiit_pet.tools.fetch_oxford_iiit_pet \
    --dest /path/to/external/oxford-iiit-pet --no-download
```

A missing archive is an error in this mode. Add `--extract` to also extract
verified archives when their extraction directories do not already exist.
The tool rejects destinations inside the executing `siderius-exp` checkout
before creating directories or fetching data.

[PROVENANCE.md](../PROVENANCE.md) records the archive sources, verification
details and split derivation.

## Manifests and runtime ownership

| File | Rows | Meaning |
|---|---:|---|
| `manifests/train.csv` | 2,946 | Canonical training identities |
| `manifests/validation.csv` | 734 | Canonical validation identities |
| `manifests/final.csv` | 3,669 | Final evaluation identities: the official test list |
| `manifests/gate2_train.csv` | 370 | Bounded training subset |
| `manifests/gate2_validation.csv` | 74 | Bounded validation subset |
| `manifests/gate2_final.csv` | 370 | Bounded final evaluation subset |
| `manifests/SHA256SUMS` | — | Verification record for the committed CSV manifests |
| `manifests/execution.json` | — | Transform settings and reference checks covering all 37 classes |

CSV columns are `image_id`, `class_index` (0–36), `official_class_id` (1–37)
and `scope`. Each `image_id` names `images/<image_id>.jpg`. The training,
validation and final identities are pairwise disjoint; bounded subsets take
the first specified number per class in committed manifest order.

[The task runtime](../runtime/pets_data_path.py) owns image decoding and the
resize, crop and tensor conversion in `decode_and_transform`.
[The identity generator](../tools/oxford_iiit_pet.py) owns split derivation;
[the execution artifact generator](../tools/oxford_iiit_pet_execution.py) owns
the bounded subsets and transform probes. These are maintenance tools;
ordinary data acquisition uses the committed manifests as supplied.
