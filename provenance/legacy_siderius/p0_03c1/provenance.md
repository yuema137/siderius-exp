# Preserved checkpoint and evidence mismatch

Source SIDERIUS revision: `95c81b7d9e2d56114bda1cdedf882f8ac4e25243`. The [manifest](manifest.json) owns
the preserved file inventory; the [directory guide](README.md) explains its scope.

The archived `configs/v17_pregate_threshold_review.json` declares evidence
SHA-256 `67ed7f17065350fb808501d9ac9a212f0e73e1ec30bfd565ed7fb0ca2c4b8323`,
while the archived `reports/health_metrics_scan.md` has SHA-256
`e631c5883e7672ff7636096735f227406a8be2cba1153ab0c4090f1a98176892`.
That mismatch is historical evidence. Neither digest, report, measurement, nor
threshold has been repaired, regenerated, or adopted by a current workflow.
