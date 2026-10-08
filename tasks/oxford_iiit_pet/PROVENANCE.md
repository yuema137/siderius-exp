# Provenance — `oxford_iiit_pet`

Historical tool/test paths below identify the original import or qualification
checkpoint. Current owners are linked in the regeneration section.

## Data source (official — use it, not Kaggle / HF mirrors, as provenance)

- **Paper**: O. M. Parkhi, A. Vedaldi, A. Zisserman, C. V. Jawahar, *Cats and
  Dogs*, IEEE CVPR 2012.
- **Dataset page**: <https://www.robots.ox.ac.uk/~vgg/data/pets/>
- **Archives** (direct download, no credential):
  - `images.tar.gz` (~792 MB) — <https://www.robots.ox.ac.uk/~vgg/data/pets/data/images.tar.gz>
    — **NOT fetched by this PR, never committed** (raw data stays outside the tree, roadmap §22.23.10)
  - `annotations.tar.gz` (~19 MB) — <https://www.robots.ox.ac.uk/~vgg/data/pets/data/annotations.tar.gz>
    (redirects to `https://thor.robots.ox.ac.uk/pets/annotations.tar.gz`) — the ONLY artifact
    consumed at PR0, from a temporary location; not committed
- **Licence** (roadmap §22.9a, frozen wording): the dataset page states
  "Creative Commons Attribution-ShareAlike 4.0 International License",
  copyright with the original image owners (re-verified 2026-08-15). The
  archive's own `annotations/README` additionally notes: "Dataset is made
  available for research purposes only. Use of these images must respect
  the corresponding terms of use of original websites from which they are
  taken." Consult the source for the authoritative current terms.

## Metadata artifact actually used (fetched 2026-08-15, twice, identical bytes)

| item | value |
|---|---|
| URL | `https://www.robots.ox.ac.uk/~vgg/data/pets/data/annotations.tar.gz` |
| fetch date (UTC) | 2026-08-15T21:57:55Z (second fetch immediately after; SHA-256 identical) |
| size | 19 173 078 bytes |
| SHA-256 (archive) | `52425fb6de5c424942b7626b428656fcbd798db970a937df61750c0f1d358e91` |
| `annotations/list.txt` | 7 355 lines (6 `#` header lines + 7 349 entries) · SHA-256 `6a54ab256e22f7a33c6f17a7669e58ea5f6f9c7a080ec2622c205aefd4b354da` |
| `annotations/trainval.txt` | 3 680 entries · SHA-256 `408f3f609481b939c94634169e6413414b733a3faeba440cbdcc5c02142eebdc` |
| `annotations/test.txt` | 3 669 entries · SHA-256 `a5454003774ffe01f4f322756d3ba5495bae21cb30bb217ab285dbfa2bef245c` |
| official format | `Image CLASS-ID SPECIES BREED-ID`; CLASS-ID 1…37; only the first two columns are identity for this task |
| consistency checks | trainval ∩ test = ∅; every id's class agrees with `list.txt`; 37 classes in each list; per-class trainval count 93–100 (roadmap said "~200 images/class, ~7,400 images": 7 349 images total, ~199/class) |

Nothing else from the archive (trimaps, xmls) is used.

## Images artifact (fetched at D14-2 C1; bytes NEVER tracked — pins only)

| item | value |
|---|---|
| URL | `https://www.robots.ox.ac.uk/~vgg/data/pets/data/images.tar.gz` |
| fetch date (UTC) | 2026-08-18T20:04:03Z |
| size | 791 918 971 bytes |
| SHA-256 (archive) | `67195c5e1c01f1ab5f9b6a5d22b8c27a580d896ece458917e61d459337fa318d` |
| independent corroboration | archive MD5 `5c4f3ee8e5d25df40f4fd59a7f44e54c` equals torchvision's official `OxfordIIITPet` resource pin — a second authority in place of a second full fetch |
| members | 7 394 tar members; 7 390 `images/*.jpg` (+ a handful of stray `.mat` the official archive ships; ignored) |
| verify/extract tool | `tools/example_packs/fetch_oxford_iiit_pet.py` (pins are module constants — the executable authority; this table mirrors them). Re-fetching `annotations.tar.gz` through the tool on 2026-08-18 re-verified its PR0 pin byte-identically. |
| lifecycle | archives + extracted `images/` live in an operator-supplied MACHINE-LOCAL directory outside the tree (`data/README.md`); the framework receives the root as the data path seam's `data_dir` (D14-2 child design §2.1) |

## Identity manifests — FROZEN derivation rule (design §3.2, OD-PR0-2)

- `final` = the official `test.txt` list (3 669 images).
- `train` / `validation` = per class, sort the official `trainval.txt` image
  ids lexicographically; the entry at 0-based position `i` goes to
  `validation` iff `i % 5 == 4`, else `train`. **No RNG, no seed — the rule
  is the provenance.** Result: train 2 946 · validation 734 (= 3 680).
- Row: `image_id, class_index (0-based = official CLASS-ID − 1), official_class_id, scope`;
  rows sorted by `(class_index, image_id)` so regeneration is byte-deterministic.
- Implementation: `tools/example_packs/oxford_iiit_pet.py` (`split_trainval`,
  `derive_manifests`); the rule is re-tested on a synthetic list in
  `tests/unit/examples/test_oxford_iiit_pet_pack.py`, independent of the fetch.

## SHA-256 pins (`data/manifests/SHA256SUMS`)

```text
f72580dcec11a5234904bacc1f98b3119c72d7bc374b9691169723502477d070  final.csv
b58e8791460ab3d5b172e7a95d4841dd603db1ecbd38bf43dafcecec522546ea  train.csv
6dfda127d8e44173064b8146600701135ea57d3a46d076859d9f91a300d7b16e  validation.csv
```

The pin is an **integrity / provenance pin**: it detects corruption and names
the exact bytes reviewed. It is NOT by itself an immutability proof (a
manifest and its pin can change together). What makes the identity canonical
is the frozen rule + the official source's recorded SHA-256 above + review of
any regeneration commit.

## Regeneration (explicit operator act)

This produces a metadata candidate for review, not a complete task package.
Run from the exp checkout root after `uv sync --group dev --frozen`, using its
own `.venv`. Replace the paths below with locations outside both repositories,
including any symlink targets. Reuse existing metadata first; if it is missing,
use the optional acquisition block below before running this recipe.

The [metadata generator](tools/oxford_iiit_pet.py) reads only `trainval.txt` and
`test.txt`; `list.txt` is recorded provenance, not a required generator input.
Verify those two inputs, then select a candidate path that does not yet exist:

```bash
set -euo pipefail
pet_metadata=/absolute/external/oxford-pet/annotations
pet_candidate=/absolute/external/regeneration/pet-metadata-candidate
(
  cd "$pet_metadata"
  sha256sum --check <<'PINS'
408f3f609481b939c94634169e6413414b733a3faeba440cbdcc5c02142eebdc  trainval.txt
a5454003774ffe01f4f322756d3ba5495bae21cb30bb217ab285dbfa2bef245c  test.txt
PINS
)
test ! -e "$pet_candidate"
test ! -L "$pet_candidate"
.venv/bin/python -m tasks.oxford_iiit_pet.tools.oxford_iiit_pet \
  --annotations-dir "$pet_metadata" \
  --root "$pet_candidate"
for split in train validation final; do
  cmp -- "tasks/oxford_iiit_pet/data/manifests/$split.csv" \
    "$pet_candidate/data/manifests/$split.csv"
done
```

The input checks print `OK`; matching CSVs make `cmp` succeed silently. A source
mismatch, existing candidate or changed CSV stops the recipe. Do not refetch over
mismatched inputs or change pins to force agreement. You must choose an external
destination; the absence checks belong to this recipe. The generator itself
can overwrite an existing root and defaults to the retired `examples/` location
when `--root` is omitted.

**Only if metadata is missing**, fetch the annotations archive into external
staging. An existing archive or extraction is never overwritten. Verify the
archive before extracting only the two required members:

```bash
set -euo pipefail
pet_stage=/absolute/external/oxford-pet
mkdir -p -- "$pet_stage"
if [[ ! -e "$pet_stage/annotations.tar.gz" && ! -L "$pet_stage/annotations.tar.gz" ]]; then
  curl --fail --location --output "$pet_stage/annotations.tar.gz" \
    https://www.robots.ox.ac.uk/~vgg/data/pets/data/annotations.tar.gz
fi
(
  cd "$pet_stage"
  sha256sum --check <<'PINS'
52425fb6de5c424942b7626b428656fcbd798db970a937df61750c0f1d358e91  annotations.tar.gz
PINS
)
if [[ ! -e "$pet_stage/annotations" && ! -L "$pet_stage/annotations" ]]; then
  tar -xzf "$pet_stage/annotations.tar.gz" -C "$pet_stage" \
    annotations/trainval.txt annotations/test.txt
fi
```

Then run the primary verification/generation recipe with `pet_metadata` set to
that stage's `annotations` directory. An interrupted download or extraction
needs operator review or a new staging directory, not an automatic overwrite.
No image archive is needed; the full [acquisition tool](tools/fetch_oxford_iiit_pet.py)
also handles images and is not this metadata-only route.

The candidate contains the three base CSVs, their checksum file and initial
model/metric declarations. It does not rebuild Gate subsets, transform probes,
Health fixtures/policy, runtime/plugins or compositions. The
[execution artifact generator](tools/oxford_iiit_pet_execution.py) separately owns
subsets and probes; [contract tests](../../tests/tasks/oxford_iiit_pet/test_package_contract.py)
cover the task package. Compare only the intended base CSVs, keep candidate
declarations for review, and never copy the candidate wholesale into `tasks/`.
Its fresh checksum file is not a replacement for the complete task's file.

Byte-identical candidates establish this metadata derivation only, not runtime
or scientific qualification. Any change to manifest bytes requires a reviewed
regeneration commit with its reason and source SHA-256 recorded here, even when
the source identity is unchanged. A change in scientific meaning also requires
a distinct task identity and corresponding implementation and provenance updates.

## Health fixture-of-record (Step 08c C3)

`expected/d14_gate2_collapse_predictions.csv` is the REAL preserved D14
Gate-2 deliverable `predictions_pets_reference_cnn_d14p_pets_gate2_001.csv`
(byte-identical copy from
`/home/klz/Data/SIDEREIS_DATA/d14_pets_gate2_20260818/`, also preserved
byte-identical in `…20260818b/`):

- sha256 `cc8470267fbf5331827c7b641ac2ce8efb834b07441a31836084d4d417ff752c`
- size 6 812 bytes
- content: 370 predictions — 369× class 5, 1× class 33 (distinct 2 of 37,
  dominant fraction 369/370 = 0.9972972972972973)

It is the constant-prediction collapse D14 deliberately preserved as
Step-08 health evidence (accuracy 0.02702702702702703 = exactly chance).
Immutable evidence: `tests/unit/examples/test_pets_health_family.py` pins
the sha256 and size, so the fixture cannot silently drift.
