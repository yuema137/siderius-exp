# TESS task execution status

## Current evidence boundary

Composed execution has been observed. The historical NoPrior unit
[nop_004](../../experiments/phyts_tess/main_fixed_workflow/runs/nop_004/RESULTS.md)
produced sixteen completed iterations and stopped at its six-hour deadline.
Its [machine-readable record](../../experiments/phyts_tess/main_fixed_workflow/runs/nop_004/results.json)
identifies infra `7689fd58b91d410788e953b51ea69a9dbc528a7d` and reports exp
`12bd80af795be8402bab0dacfca6968054554b1d`.

The separate paper-startup audit retains an unknown original exp revision for
that same unit. The [paper artifact reference](../../experiments/paper-artifacts.md)
records this difference in provenance certification. Do not treat either historical
receipt as a new qualification of the repository's current framework pin.

The task declarations, loaders, scoring and Health plugins remain owned here.
The [fixed workflow](../../experiments/phyts_tess/main_fixed_workflow/README.md)
owns treatment and launch settings. Tutorial execution has separate, smaller
budgets and [separate provenance](../../tutorials/paper/examples/README.md).

## Limitations

- The recorded score is validation R², not a held-out test result or reproduction
  of published PhyTS test figures.
- The historical run has no independent replicate. It does not establish
  significance between its candidate scores.
- The dispersion check is an observational task declaration; passing it does
  not establish scientific usefulness. The poor negative-R² model in the run
  also passed its configured dispersion floor.
- A new source pair or changed task/configuration needs its own qualification.
  This documentation audit performed no new training, provider calls or Gates.

## Earlier component checks

The following dated observations describe the initial in-process qualification,
before the later composed run. They remain evidence for that earlier scope.

### Component observations (2026-09-20)

Run from this checkout's own `.venv/bin/python`, against the real released
data staged into a run data root.

| check | result |
|---|---|
| pack contract suite, `tests/tasks/phyts_tess` | **13 passed** with `PHYTS_TESS_DATA_DIR` set; 12 passed + 1 honest skip without |
| split independence | train 3,338 curves / 505 stars, val 442 / 64, **star overlap 0** |
| planted-leak counterexample | a star admitted to both scopes IS detected |
| sub-portion draw | `portion=0.1` drew 341 curves / 55 stars, every star whole, zero leak into val |
| scope codec | serialize → deserialize → serialize is byte-identical, and rebuilding the same request does not drift |
| materialization | `[1, 1024]` float32 input, `[1]` float32 target, 442 rows for a 442-row scope |
| reference model | 18,433 parameters, `[442, 1, 1024] → [442, 1]` |
| deliverable | write then read covers the scope exactly |
| scoreability | healthy deliverable passes with zero failures |
| metric arithmetic | `r2(truth=[1,3], pred=[2,3]) = 0.5` and `rmse = 0.707106781186548`, both matching independent hand computation |
| R-squared identity | the constant-mean predictor scores **exactly** `0.000000000000000` |
| partial deliverable | refused, naming the coverage shortfall |
| staging guard | refuses a destination holding a test artifact, **exit code 1** |

An untrained reference CNN over the full validation scope scored
`r2 = -4.688`, `rmse = 1.340`, `mae = 1.218`. That is an execution
observation, not a baseline: the network was never trained.
