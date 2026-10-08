# TIDMAD anchor staging contract

Scope: the approved scoring anchor in an external `data_dir`. The
[human preparation guide](README.md#stage-the-approved-anchor) owns the staging
command. This reference owns reader locations, exact identity and provenance
requirements; it does not authorize changing an existing data root or run.

## Readers and approved identity

The composed metric's
[`_task_owned_score_kwargs`](../runtime/scoring.py) and the Trial adapter's
[`trial_anchor_path`](../runtime/tidmad_data_path.py) select
`data_dir/segment_anchors.json`. They do not automatically use the copy shipped
in the task. Stage that file before making the data root read-only, and verify
byte equality again before an affected fresh run.

The approved source is
[`tasks/tidmad/reference_data/segment_anchors.json`](../reference_data/segment_anchors.json).
Its SHA-256 is:

```text
0c44b6084dc8afc4dc2fa34f5253bc8d780b4e8ae086945e7051d8bf7928ba90
```

The README command copies only when neither a file nor a symbolic link exists
at the destination, uses `cp --no-clobber`, then compares source and destination
with `cmp`. A differing file, unreadable destination or dangling link must stop
preparation; do not overwrite an existing ruler, regenerate anchors or
recalibrate to make a run proceed. No HDF5 file is copied.

For a fresh run's provenance, retain the comparison result and both source and
staged SHA-256 values. With the variables from the README staging command, record:

```bash
sha256sum -- "$tidmad_anchor" "$tidmad_data_dir/segment_anchors.json"
```

Both values must equal the approved digest above. The canonical JSON remains
the scoring artifact; this reference records its identity and must not be used
to justify changing frozen evidence.

## Preflight coverage

- The [Gold campaign preflight](../../../campaigns/tidmad_gold/scripts/campaign_preflight.sh)
  checks staged anchor presence when required. That presence check does not
  establish equality with the approved source.
- Gold pooled Stage3 uses the committed anchor through
  [campaign paths](../../../campaigns/tidmad_gold/paths.py). This separate reader
  does not certify the composed metric's staged input.
- The [main fixed-workflow band verifier](../../../experiments/tidmad/main_fixed_workflow/band_inputs.py)
  verifies selected HDF5 file identities and compares the staged anchor with
  the committed anchor. Its stricter check does not change the Gold presence
  check's coverage.

These instructions do not change a real-data directory or historical workspace
until an operator performs the staging step. Preserve existing run inputs and
receipts; a corrected staging procedure is not new execution qualification.
