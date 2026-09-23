# Project8 fixed workflow: both time and frequency inputs

This experiment binds the [dual-representation task](../../../tasks/phyts_project8/DUAL_REPRESENTATION.md)
to the existing fixed workflow. Human advice and Data Analysis remain explicitly
disabled; literature review remains enabled. The expanded physical task context
and mandatory use of both views are new task conditions, so this run must be
reported separately from the historical time-input run even though its
information-treatment module switches remain NoPrior.

## Frozen settings

- 24-hour unit, H100, at most 100 iterations.
- One Trial and one Formal round per iteration.
- Trial/Formal total attempt budgets: 30/120 minutes; VRAM: 40/40 GB.
- Formal training pool and per-epoch fraction: both 1.0 (40,000 rows).
- Training validation loss: fixed 500 rows; final scoring: all 5,000 validation rows.
- At most 100 epochs; training budget reserve fraction 0.2; prediction watchdog off.
- Training-pool target standardization; best-validation checkpoint; partial batches retained.

Only the task composition, experiment identity and agent-file path differ from
`main_fixed_workflow`. No old workspace or calibration is inherited.

## Readiness

The offline view, composition and focused tests are preparation evidence.
A formal run additionally requires a clean frozen exp revision, its exact infra
pin, verified deployed data, short native/agent qualification (including actual
use of both input views), and a new unit/start receipt. No formal start is
implied by this directory. Launch through `experiments.shared.prepared_workflow_unit`
using this experiment directory and the new prepared data root.
