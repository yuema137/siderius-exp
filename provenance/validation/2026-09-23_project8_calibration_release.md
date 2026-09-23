# Project8 calibration release binding

This release updates only the exact SIDERIUS dependency to
`349b6cd6d9766abbf3d87515b22e1005599a694b` (`v0.2.16`, infra PR #579).
`SIDERIUS_REVISION`, `pyproject.toml`, and `uv.lock` agree.

The repair excludes training between validation passes from validation's
calibration window. It preserves active validation setup/loading/compute time,
evidence requirements, total training allocation, and campaign deadlines.

The real H100 qualification retained the generated model, batch size 8,
40,000 training rows per epoch, 500 loss-validation rows, and 5,000 scoring rows.
Measured admission was enabled with the default 60-second calibration window;
prediction watchdog was disabled. A qualification-only three-epoch/600-second
bound completed training, inference and scoring. Validation verified with about
0.517 seconds of active time while excluding 98.24 seconds of intervening
training. Independent scoring and checkpoint/target-transform checks passed.
Infra automatic CI passed. This is execution evidence, not a quality claim.

Task package, input representation, splits, formal parameters, LLM settings,
information treatment and data hashes remain unchanged from exp rc.35.
A formal restart requires a fresh unit and immutable 24-hour clock. It must
not resume the stopped unit or seed from diagnostic candidate artifacts.
