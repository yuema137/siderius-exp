# Paper experiment compatibility acceptance

Status: offline shared-strategy comparisons pass; see [the scoped verification
report](paper-parity.md). Historical archive recovery is no longer a merge
condition. Normal current startup still includes three training-schema fields
added before #372; the operator accepted that pre-existing difference outside
this PR. Scoped verification is complete. Do not describe it as an exact
historical request replay.

## Operator requirement and scope

The operator revised acceptance on 2026-10-05: verify LIGO prompt text offline,
audit the other three paper experiments for shared logic and historical-provider
identity, and add comparisons only for their additional branches. Recovering
retired predictions is explicitly not a merge condition. No LLM request or GPU
training is needed. The original formal lineages below remain the source for
this audit; tutorial demos are not substitutes.

The earlier archive census remains provenance. Its missing transcripts and
retired artifacts describe limits on full historical replay, not new gates
added to this narrower strategy-migration acceptance.

The local paper checkout is `SIDERIUS-Paper`, revision recorded in
`paper-source-inventory.json`. Its `iclr/data/cross_task_progress.json` identifies:

| Task | Original source unit | Infra revision |
| --- | --- | --- |
| TESS | `nop_004` | `7689fd58b91d410788e953b51ea69a9dbc528a7d` |
| LIGO | `ligo-no-prior-run2` | `0ab1573602c708ddd182432ad4d0e43ae4828c53` |
| Project 8 | `project8-dual-no-prior-run5` | `349b6cd6d9766abbf3d87515b22e1005599a694b` |

All three local launch-file SHA-256 values match the paper's recorded values.
Independent review also checked the referenced record/manifest hashes: 33 for
TESS, 35 for LIGO and 24 for Project 8; all matched. These counts are hash
comparisons, not iteration counts or complete artifact inventories.

TIDMAD's `iclr/data/tidmad_unified_table_inputs.json` identifies six systems
across four bands: 24 system/band scopes. Its source snapshot hash matches
`iclr/supplement/review/unified_current.json`. The directly affected native
workflow subset is eight units:

- `workflow-v5-20260919`: NoPrior, all four bands, infra `345c802d`.
- `workflow-da-only-run1-20260922`: Data Analysis, all four bands, infra `c0467447`.

The full revisions, launch digests and paper source-archive mappings are in the
inventory. The coding-agent and external-orchestrator baselines remain distinct
lineages. Do not assign a native planner plugin to them without demonstrating
that they consume that interface. Their presence in the paper must remain in
the artifact census; their prompts are not implicitly covered by native tests.

## What has been verified

All five native infra revisions above have identical bytes for:

- `src/agent/prompts.py`: `9b78d505cb11786319aca45e763f48d73d235e0f7e9de6fb3a62ffc774d237bd`.
- `src/agent/llm_bridge.py`: `db399f241a3a70ac250890b9940daf244981554e87cd033a69902cec121a49bf`.
- `src/agent/prompt_templates/tuner/loss_rendering.py`: `9af47ab18d2a2e443023e12d5afc15403a9844a34e2c76459d485d25709882a4`.

The archived template and conditional loss helper are preserved by this package.
That does not complete the assembly audit. In particular, planning code in
`345c802d` and `7689fd58` predates the independent training-validation disclosure;
`c0467447`, `0ab15736` and `349b6cd6` include it. Determine whether each actual
run supplied the relevant configuration before attributing a prompt difference.
Other planning differences include scope-count reporting and Formal recovery
context. Equal template hashes alone do not prove all final messages match.

## Evidence gaps found

Unit-level filename inventories found no final prompt/request/response artifacts
for TESS, LIGO or Project 8. The eight TIDMAD workflow units likewise had no
non-control equivalents identified. Token usage records contain counts and
components, not complete messages. Data Analysis `control/.../response.json`
files are execution responses; a sampled file contains status, validated
parameters and payload, not an LLM completion. Filename search is scoped
absence evidence, not proof that no separate backup or embedded transcript exists.

Prediction-retention receipts explicitly record retired outputs:

| Native lineage | Retired output entries (including completion markers) |
| --- | ---: |
| TESS `nop_004` | 33 |
| LIGO run2 | 35 |
| Project 8 dual run5 | 24 |
| TIDMAD NoPrior, bands 0–3 / 4–9 / 10–14 / 15–19 | 216 / 312 / 250 / 230 |
| TIDMAD Data Analysis, same band order | 208 / 288 / 240 / 240 |

This is documented retention behavior, not an allegation of corruption. It does
not imply checkpoints or model source were deleted: sampled TESS checkpoint
receipts retain the scored checkpoints. A retention digest proves what bytes
were retired; it does not supply those bytes. The operator identified
`/home/klz/Data/SIDERIUS-ICLR` for a broader backup search. Do not redownload
raw datasets or modify original archives.

## Additional archive search (2026-10-05)

The read-only search listed 311,446 files, including hidden files, under the
operator-provided archive root. Both `diagnosis/` and the distinct `diagosis/`
directory were included. All 63 recognized tar/zip containers were inventoried
without extracting or executing their contents. This is a bounded inventory,
not a claim that every possible encoding or external backup was searched.
Nested containers, transformed encodings and external symlink targets were not
recursively searched.

The 2,076 retired entries across the eleven native units comprise 92 prediction
JSON files, 992 TIDMAD HDF5 outputs and 992 completion markers. Matching by
original basename or byte size selected 163 loose files and 13 container members
for SHA-256 comparison. The search found one prediction file whose bytes match
its original retention digest:

- LIGO run2, iteration 17, candidate
  `replicated_compact_four_band_ridge_gate_iter_017_002`.
- Backup directory:
  `runs/phyts-no-prior-20260922/ligo/run2/workspace/iter_017/iteration_017/replicated_compact_four_band_ridge_gate/`.
- SHA-256:
  `19ece2d8ae26ab8bebdd2d018f60c631a46dd25a41fe8271cbd74ef57b491ca1`.

The other 25 loose-file matches are completion markers sharing one digest.
They do not recover prediction arrays and do not establish experiment identity.
No container member matched a retired digest. No original receipt was changed,
and finding the LIGO copy does not qualify the entire run for replay.

Structured CLI transcripts were also found in four TIDMAD paper lineages:

| Archive lineage | JSONL files with role-bearing messages |
| --- | ---: |
| `claude-20260918-201900Z` | 604 |
| `codex-20260917-162321Z` | 56 |
| `orchestration-noprior-run2-20260920` | 34 |
| `orchestration-da-only-run1-20260924` | 60 |

These counts are files, not independent calls or validated paper candidates.
Their JSONL records parsed without malformed lines in this selection. Codex
and orchestration traces include compaction events, so the existence of
user/assistant messages does not prove preservation of every complete provider
request. Claude traces likewise have not been qualified as full request bodies.
The next replay audit must establish call ordering, candidate association and
coverage before using these traces as an oracle. They do not establish native
workflow planner-message preservation. Raw traces remain local; this report
publishes only structural counts and artifact digests.

A separate content search scanned 108,650 JSON, JSONL, log and text files for
request/message keys and prompt markers, excluding source checkouts, dependency
environments, separately inspected CLI traces and credential filenames. Its 92
file matches comprised 82 token-usage logs, four diagnostic Codex invocation
logs and six Claude SDK cache-state files. All 13,296 component values in the
4,962 token-usage rows were integer counters, not prompt text. The other matches
belong to CLI or diagnostic evidence; none establishes original native planner
requests for the paper units. This search did not recover the missing native
per-call message archive. Key-based search cannot rule out other field names,
file formats or encodings.

Independent review confirmed the retired-entry counts, the LIGO digest/size
match and the distinction between marker and prediction recovery. Exact
paper-wide prompt and artifact reproduction remains unverified.

## Current verification boundary

The report records LIGO production-startup captures, two sets of twelve final
system/user comparisons, source and launch-configuration mappings for eleven
native units, and the pre-existing schema differences. The provider is
`legacy-9b78d505cb11-v1` for all audited native paper consumers. Original records
and locks remain immutable; this audit does not resume or rewrite them.

These checks establish scoped prompt compatibility, not regenerated model
weights, recovered provider requests, or replayed scientific results. The 28
earlier synthetic comparisons and 18 real TESS calls retain their original
bounded meaning. No fresh stochastic call is part of this verification.
