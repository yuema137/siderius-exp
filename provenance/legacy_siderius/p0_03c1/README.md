# P0 03C1 legacy SIDERIUS archive

This directory preserves 46 exact files from the [recorded pre-removal
checkpoint](provenance.md). The paths below this directory reproduce the original
SIDERIUS paths. The [manifest](manifest.json) records the original locations
and file identities.

The archive is provenance only. Its scripts are not supported launchers, its
tests are not collected as part of the live `siderius-exp` suite, and its
configuration and reports are not current experiment inputs. Historical files
retain old checkout paths, task defaults, provider-variable names, treatments,
and evidence references verbatim; reproducing one requires a separate review of
its original dependencies and revision. Missing historical dependencies have
not been invented or recovered.

## Current live owners

- TIDMAD anchor construction, loading, and task-local default resolution live
  in `tasks/tidmad/runtime/anchor_map.py`.
- The sole live canonical anchor artifact remains
  `tasks/tidmad/reference_data/segment_anchors.json`; it was already
  byte-identical to SIDERIUS's copy and was not recopied here.
- Current numerical and tool contracts remain under
  `tests/tasks/tidmad/reference/` and the adjacent live TIDMAD tool tests.
- Generic framework protections for study/process/CI behavior remain a
  SIDERIUS responsibility. Archiving original study tests here does not replace
  those protections or authorize their deletion.

The preserved threshold-review configuration and report disagree about the
expected evidence identity. This mismatch remains part of the historical
record; no report, measurement or threshold was repaired or adopted. See the
[provenance note](provenance.md).

This preservation checkpoint records the pre-cleanup state. The #430 cleanup
has since removed 44 duplicated originals plus the root anchor; two live Slurm
files remain for the separately approved 03C2 migration. The 46 archived files
and this manifest remain unchanged historical evidence.
