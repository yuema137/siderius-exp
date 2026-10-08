# Provenance — `davis_future_prediction`

Historical tool/test paths below identify the original import or qualification
checkpoint. Current owners are linked in the regeneration section.

## Data source (official)

- **Paper**: J. Pont-Tuset, F. Perazzi, S. Caelles, P. Arbeláez, A. Sorkine-Hornung,
  L. Van Gool, *The 2017 DAVIS Challenge on Video Object Segmentation*,
  arXiv:1704.00675 (2017) — <https://arxiv.org/abs/1704.00675>.
- **Challenge page / downloads**: <https://davischallenge.org/davis2017/code.html>
  → `DAVIS-2017-trainval-480p.zip` (~833 MB, hosted at `data.vision.ee.ethz.ch`),
  direct download, no credential (HEAD-checked 2026-08-15 at the roadmap
  selection audit). **NOT fetched by this PR; its body is never read; never
  committed** (roadmap §22.23.10).
- **Official tooling**: <https://github.com/davisvideochallenge/davis-2017>
  (the challenge's published toolkit) — its `data/db_info.yaml` is the
  official sequence-list METADATA consumed at PR0 (below).

## Licence / provenance wording (frozen — roadmap §22.9a, per artifact)

The official DAVIS repository (fperazzi/davis README) states "DAVIS is released
under the BSD License"; the challenge-created annotations carry separate
CC BY 4.0 terms (2017 challenge rules); the challenge download page itself
states no licence. This SIDERIUS task consumes RGB FRAMES, not segmentation
annotation masks — no single licence is claimed for every DAVIS artifact.

### D14-3 VERIFICATION (2026-08-18) — the PR0 obligation, discharged

Primary sources re-checked on the fetch date:

| source | finding (verbatim where quoted) |
|---|---|
| `davischallenge.org/davis2017/code.html` (the download page) | **no licence stated**; research framing: "feel free to use the full resolution ones (4k, 1080p, etc.) in any step of your research" |
| `davischallenge.org` (main page) | **no licence stated**; "Please cite the relevant papers in your publications if DAVIS helps your research." |
| `github.com/davisvideochallenge/davis-2017` `LICENSE` (official toolkit) | **BSD 3-Clause**, "Copyright (c) 2016, Federico Perazzi / All rights reserved." |
| challenge ANNOTATIONS (CC BY 4.0, 2017 rules) | **NOT consumed** — this task reads RGB frames only (frozen §22.9a) |

**Verdict: COMPATIBLE with this task's executable path.** The use is
machine-local research evaluation of RGB frames, with SHA-pinned provenance
and **zero redistribution** (this repository stores pins and derived
identity/clip manifests, never dataset bytes); the requested citations are
recorded above. No term found in any primary source conflicts. Should the
publishers later state terms that do conflict, this row is what must be
re-checked.

## Frames artifact (fetched at D14-3 C1; bytes NEVER tracked — pins only)

| item | value |
|---|---|
| URL | `https://data.vision.ee.ethz.ch/csergi/share/davis/DAVIS-2017-trainval-480p.zip` (the official link on the challenge download page) |
| fetch date (UTC) | 2026-08-18T21:03:15Z |
| size | 832 766 765 bytes |
| SHA-256 (archive) | `e3d0b5b77c3d031b000a19e0e25e3e2cac65d183755601bc2cf066df1a2aa492` |
| extracted layout | `DAVIS/JPEGImages/480p/<sequence>/%05d.jpg` — all **90** sequences named by the frozen `sequences.csv` verified present with frames (`fetch_davis.py --check-layout`) |
| verify/extract tool | `tools/example_packs/fetch_davis.py` (pin is a module constant — the executable authority; a test asserts this table mirrors it) |
| lifecycle | archive + frames live in an operator-supplied MACHINE-LOCAL directory outside the tree; the framework receives the root as the data-path seam's `data_dir` |

## Metadata artifact actually used (fetched 2026-08-15; NO archive body)

| item | value |
|---|---|
| source | `https://raw.githubusercontent.com/davisvideochallenge/davis-2017/97d08bf8b6201abf15509a67a985db3745a75ccd/data/db_info.yaml` (pinned commit `97d08bf8`, 2017-06-07; identical bytes at `master` on the fetch date) |
| fetch date (UTC) | 2026-08-15T22:04:49Z |
| size | 12 688 bytes |
| SHA-256 | `b14a9c264d04ffc6f99a92985fe024a388a7ee08e115f65e4005b72527420c4b` |
| content used | `sequences[].name` and `sequences[].set` for `set ∈ {train, val}` ONLY — 60 `train`, 30 `val` (the file also lists 30 `test-dev` sequences and per-sequence `num_frames`; neither is consumed — `num_frames` is clip-level information and belongs to D14) |
| consistency | train ∩ val = ∅; no duplicate names; counts equal the official DAVIS 2017 TrainVal split (60 / 30) |

## Sequence identity — FROZEN derivation rule (design §3.3, OD-PR0-2)

- `train` = the 60 official train sequences.
- `validation` / `final` = the 30 official val sequences sorted by name; the
  entry at 0-based position `i` goes to `validation` iff `i % 2 == 0`, else
  `final` — 15 / 15, sequence-disjoint by construction. No RNG, no seed.
- Row: `sequence_name, scope`; rows sorted by scope order
  (train, validation, final) then by name — byte-deterministic regeneration.
- Implementation: `tools/example_packs/davis_future_prediction.py`
  (`parse_db_info`, `split_official_val`, `derive_sequence_manifest`); the
  rule is re-tested on a synthetic list in
  `tests/unit/examples/test_davis_future_prediction_pack.py`.
- **Clip identity `(sequence_name, start_frame)` is NOT derived here** — D14
  in full (operator, 2026-08-15). PR0 has no archive-listing / HTTP-range
  machinery.

## SHA-256 pin (`data/manifests/SHA256SUMS`)

```text
56ddf30f02c8d8cba0a4a4839a32e0c8e0d9e00609c81d93be6b5edf5e9656b2  sequences.csv
```

An **integrity / provenance pin** — it detects corruption and names the exact
bytes reviewed; it is NOT by itself an immutability proof. Canonical identity =
the frozen rule + the official metadata's recorded SHA-256 above + review of any
regeneration commit.

## Regeneration (explicit operator act)

This produces a metadata candidate for review, not a complete task package.
Run from the exp checkout root after `uv sync --group dev --frozen`, using its
own `.venv`. Replace the paths below with locations outside both repositories,
including any symlink targets. Reuse existing metadata first; if it is missing,
use the optional acquisition block below before running this recipe.

The [metadata generator](tools/davis_future_prediction.py) reads the pinned
`db_info.yaml` without downloading or inspecting frames. Verify that input,
then select a candidate path that does not yet exist:

```bash
set -euo pipefail
davis_metadata=/absolute/external/davis-metadata
davis_candidate=/absolute/external/regeneration/davis-metadata-candidate
(
  cd "$davis_metadata"
  sha256sum --check <<'PINS'
b14a9c264d04ffc6f99a92985fe024a388a7ee08e115f65e4005b72527420c4b  db_info.yaml
PINS
)
test ! -e "$davis_candidate"
test ! -L "$davis_candidate"
.venv/bin/python -m tasks.davis_future_prediction.tools.davis_future_prediction \
  --db-info "$davis_metadata/db_info.yaml" \
  --root "$davis_candidate"
cmp -- tasks/davis_future_prediction/data/manifests/sequences.csv \
  "$davis_candidate/data/manifests/sequences.csv"
```

The input check prints `OK`; a matching CSV makes `cmp` succeed silently. A
source mismatch, existing candidate or changed CSV stops the recipe. Do not
refetch over mismatched inputs or change pins to force agreement. You must choose
an external destination; the absence checks belong to this recipe. The generator itself can
overwrite an existing root and defaults to the retired `examples/` location
without `--root`.

**Only if metadata is missing**, fetch the small pinned source file. An existing
file, including a dangling symlink, is never overwritten:

```bash
set -euo pipefail
davis_metadata=/absolute/external/davis-metadata
mkdir -p -- "$davis_metadata"
if [[ ! -e "$davis_metadata/db_info.yaml" && ! -L "$davis_metadata/db_info.yaml" ]]; then
  curl --fail --location --output "$davis_metadata/db_info.yaml" \
    https://raw.githubusercontent.com/davisvideochallenge/davis-2017/97d08bf8b6201abf15509a67a985db3745a75ccd/data/db_info.yaml
fi
```

Then run the primary verification/generation recipe with that metadata directory;
the downloaded file must pass its recorded pin before use. An interrupted fetch
needs operator review or a new staging directory, not an automatic overwrite.
No frame archive or extraction is needed; [frame acquisition](tools/fetch_davis.py)
is a separate operation. The generator also accepts two official one-name-per-line
lists via `--lists`, but those inputs need their own source verification and are
not covered by the `db_info.yaml` pin.

The candidate contains `sequences.csv`, its checksum file and initial model/metric
declarations. It does not rebuild clip identities, execution probes, Health
policy, runtime/plugins or compositions. The
[execution artifact generator](tools/davis_execution.py) separately owns clips
and probes; [contract tests](../../tests/tasks/davis_future_prediction/test_davis_package_contract.py)
cover the task package. Compare only `sequences.csv`, keep candidate declarations
for review, and never copy the candidate wholesale into `tasks/`. In particular,
the writer's sequences-only `SHA256SUMS` would replace the complete task's file
if pointed at a populated task root.

Byte-identical candidates establish this metadata derivation only, not runtime
or scientific qualification. Any changed manifest needs a reviewed regeneration
commit with its reason and source pin recorded here. A change in scientific
meaning also requires a distinct task identity and corresponding implementation
and provenance updates.

## Health threshold provenance (Step 08c C4)

`declared/task_health.yaml` freezes `min_dispersion = 0.04` against the
ONE preserved healthy real artifact (NOT in the repo — 17.9 MB,
machine-local beside the D14 corpus):

- `/home/klz/Data/SIDEREIS_DATA/d14_davis_gate2_20260818c/predictions_davis_reference_predictor_d14d_davis_gate2_001.npz`
- sha256 `ee52a7109798a1c4c608e7824e623604e2986dab8d499b75a4794d443e0fa010`
- 15 float32 clips `[3,4,128,224]`, n = 5,160,960 samples, all finite
- population dispersion (full decoded view, `np.std(..., dtype=np.float64,
  ddof=0)`) = `0.2156402715035823` — measured ONCE at design freeze and
  reproduced bit-equal by the skip-guarded test in
  `tests/unit/examples/test_davis_health_family.py`.

Honest caveat: exactly one healthy real artifact exists, so 0.04 is a
safety floor against near-constancy in the deliverable's native units,
not a calibrated healthy-population statistic. No sweep or re-measurement
is performed.
