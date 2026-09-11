# P0 03C1 legacy SIDERIUS archive

This directory preserves 46 exact files from SIDERIUS revision
`95c81b7d9e2d56114bda1cdedf882f8ac4e25243` before their proposed removal
from the active framework tree. The paths below this directory reproduce the
original SIDERIUS paths. [`manifest.json`](manifest.json) records every source
path, destination, byte count, and SHA-256 digest.

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

The archived `configs/v17_pregate_threshold_review.json` declares evidence
SHA-256 `67ed7f17065350fb808501d9ac9a212f0e73e1ec30bfd565ed7fb0ca2c4b8323`,
while the archived `reports/health_metrics_scan.md` has SHA-256
`e631c5883e7672ff7636096735f227406a8be2cba1153ab0c4090f1a98176892`.
That mismatch is historical evidence. Neither digest, report, measurement, nor
threshold has been repaired, regenerated, or adopted by a current workflow.

This preservation checkpoint records the pre-cleanup state. The #430 cleanup
has since removed 44 duplicated originals plus the root anchor; two live Slurm
files remain for the separately approved 03C2 migration. The 46 archived files
and this manifest remain unchanged historical evidence.
