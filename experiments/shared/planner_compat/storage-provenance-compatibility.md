# Scoped-storage historical presentation contract

## Ownership and qualified references

SIDERIUS issue #419 repairs storage evidence when the calling process cannot
observe the setup reads. Infra owns truthful current observations. This package
owns the explicitly selected paper-era planner view; it does not change saved
records, execution, admission, calibration, or storage-counter collection.

Version 0.7.0 adds `legacy-9b78d505cb11-paper-storage-v7` and
`legacy-9b78d505cb11-paper-late-storage-v7`. They wrap the corresponding v6
provider, preserving its earlier manual, ordering, attempt-role, runtime-feedback
and passing-preflight projections. Neither becomes an installation default.
The new identity requires a new workspace; existing locks are not migrated.

The [source matrix](src/siderius_planner_compat/fixtures/storage_reference_matrix.json)
pins five exact framework revisions for TESS, LIGO, Project8, TIDMAD NoPrior and
TIDMAD analysis-on. Their `provenance.py` bytes are identical, and their
`_setup_storage_provenance` ASTs are identical. Therefore all five use the same
physical scoped byte basis and cache classifier. `legacy_storage_4e46ced5.py`
contains the classifier verbatim. Its module hash is verified before provider
construction, and its source hash is checked against the reference matrix.

The profile identity fingerprints the frozen classifier, source matrix, v7
projection source, qualified current infra provenance source, and full v6 identity. Changing any of those changes the
selected scientific treatment identity. The filesystem-name heuristic exists
only in this frozen experiment renderer; current infra uses explicit coverage.

## Projection and failure behavior

`project_record` recursively copies each raw planner history record. A missing
runtime-verification block or storage block passes unchanged. A storage mapping
without any of the four #419 fields is already historical and also passes
unchanged. No historical timestamps, counters, sizes, RSS, or setup durations
are fabricated.

Presence of any new field requires the complete qualified storage shape:

- Existing dataset root, file counts, expected raw bytes, total file bytes,
  filesystem type, process counter delta, cache state and before/after RSS.
- `expected_on_disk_bytes`, `process_read_bytes_scope`,
  `process_read_bytes_reason`, and `cache_state_unknown_reason`.

The private Pydantic boundary refuses extra fields, missing fields, wrong types,
negative byte sizes, inconsistent file counts, differing old/new byte bases,
unknown coverage values, and cache states contradicting incomplete coverage.
Current cache state and its exact reason must match the public infra
`assess_cache_state` authority for the retained counter, byte basis, coverage
and task reason. V7 verifies the complete current `provenance.py` source hash
against its matrix before using that authority; an unqualified producer
refuses profile construction before rendering. This is a bounded producer
contract, not a best-effort field-removal filter. New producer sources or
shapes require fresh qualification. The current classification formula is
not copied into the experiment package.

On that validated copy, the frozen classifier reconstructs `cache_state` from
`bytes_read_from_storage`, `expected_raw_bytes`, and `filesystem_type`. It then
removes only the four new fields. All remaining values and insertion order
stay intact. An incomplete current counter may consequently appear warm in
the historical prompt: that is the explicitly requested old representation,
not the actual current evidence, which remains unknown in the saved record.

For example, a current record with 100 physical bytes, process delta 0 and
unknown coverage keeps `cache_state="unknown"` on disk. With an `ext4`
historical filesystem label, v7 renders the old `warm_page_cache` value and old
field shape. The native planner still sees corrected evidence. This package
does not assert that the old classification was scientifically reliable.

## Offline evidence and commands

The check is deterministic prompt reproduction, not scientific replay or proof
that future LLM outputs match. No API, GPU, training, cache eviction or external
scientific data reads are needed.

For the exact current infra/consumer pairing, install the package normally into
that infra checkout's own frozen environment, then run the entire planner
compatibility test directory with its Python:

```bash
uv pip install --python "$INFRA_CHECKOUT/.venv/bin/python" --no-deps \
  "$EXP_CHECKOUT/experiments/shared/planner_compat"
"$INFRA_CHECKOUT/.venv/bin/python" -m pytest \
  "$EXP_CHECKOUT/experiments/shared/planner_compat/tests" -q
```

The published exp infra pin remains unchanged and predates the qualified
current storage assessor. V7 refuses that producer. Its tests under the
exp-owned frozen environment report 2 passed and 40 skipped; this is not
current-producer acceptance evidence. At infra `bf42f26c`, all 86 planner
compatibility tests passed with package 0.7.0 installed, including all 42 v7
tests and all v6 tests. No current-producer case skipped in that pairing.

V7 tests compare complete system/user request pairs at `LLMBridge.plan`, where
the bridge intercepts provider invocation and refuses network access. Four
archived task record shapes come from the existing prompt-compat fixtures.
TESS, LIGO and Project8 contain real storage observations; their unprojected
new-format request differs and v7 restores the prior request. The selected
TIDMAD NoPrior archive has no storage observation and remains unchanged. The
analysis-on reference is source-qualified; this test does not claim a captured
full analysis-on historical planner request. Both early/late providers also
cover cold threshold boundaries, warm reads, unavailable counters, empty byte
bases, and the historical unsupported-filesystem behavior. Ten malformed or
inconsistent input classes and five contradictory complete-coverage cases
refuse before a captured provider request. Five consistent complete-coverage
cases preserve the old request, including missing/decreasing counters and a
current complete counter whose historical filesystem heuristic said unknown.
A changed current-producer source refuses profile construction.

To verify explicit reference checkouts without importing their code, provide
a JSON mapping with exactly `tess`, `ligo`, `project8`, `tidmad`, `analysis`, each
mapped to the matching checkout path, then run:

```bash
.venv/bin/python experiments/shared/planner_compat/storage_reference_check.py \
  --references /path/to/reference-checkouts.json \
  --output /path/to/storage-reference-check.json
```

The command verifies Git HEAD, complete provenance source SHA-256 and setup
helper AST SHA-256. All five reference checks passed on 2026-10-07. Recorded
results are in [the qualification evidence](evidence/storage-provenance-reference-check.json).
