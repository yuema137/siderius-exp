# STATUS — `phyts_tess` (honest maturity)

## Maturity: **declarations complete; composed production execution NOT YET RUN**

Every family a composed run needs is declared and every unit of it has been
exercised in process. **No SIDERIUS chain has executed this task.** Nothing
below should be read as a qualification.

## What has actually been verified (2026-09-20)

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

## What is NOT claimed

1. **No composed run.** `run_chain.sh` has never been pointed at this
   composition. Manifest resolution, child-process scope transport, Health
   materialization inside a real round, and resume behaviour are all
   unverified here.
2. **No scientific result.** No model has been trained. The PhyTS reference
   figures (S4D 0.665, LinOSS 0.612, CNN 0.617, mean baseline -0.017) are
   quoted from the paper and were not reproduced.
3. **No Gate evidence.** Neither Gate 1 nor Gate 2 has been run.
4. **Health thresholds are provisional.** The dispersion floor is derived
   from the target spread, not from a measured healthy prediction artifact,
   and its disposition is `recording` for exactly that reason.
   `declared/task_health.yaml` carries the promotion path.
5. **The held-out test split has never been read.** No number in this
   repository was computed against it.

## Next

A composed `--dry-run` against a real experiment, then a bounded real run.
Until one exists, this package is a declaration that type-checks and whose
units compute — which is less than it looks like.
