# TIDMAD orchestrator information-treatment scope

Operator decision: 2026-09-18. This is an additive experiment declaration for
O-Full and O-NoPrior, not a change to the frozen common task or generic toolbox.
Read it together with `SIDERIUS-RUN.md` in the assembled agent workspace.

## Scope of the common package's advice statements

The no-advice statements in the common `input/task.md` and the advice state in
`input/treatment.json` describe the **CLI baseline condition**. In particular,
the statement that advice is allowed only at `input/advice.json` when
`input/treatment.json` enables it applies to that CLI condition.

For O-Full and O-NoPrior, the operator-approved additional orchestrator treatment
in `SIDERIUS-RUN.md` determines the dedicated Data Analysis and initial human
advice state instead. The absence of `input/advice.json` is expected and does
not disable an explicitly declared O-Full artifact outside the frozen input.
Preserve every common input file, including its original treatment and provenance.

## Joint selector and supplied information

| Explicit run declaration | Dedicated Data Analysis | Model research advice | Controller strategy advice | Literature review |
| --- | --- | --- | --- | --- |
| O-Full / prior on | Enabled | Exact declared artifact at `run/advice.json` | Exact declared artifact at `run/controller-work-strategy.md`, outer controller only | Enabled |
| O-NoPrior / prior off | Disabled, no findings injection | Absent | Absent | Enabled |

These paths are relative to the assembled agent workspace containing
`SIDERIUS-RUN.md`; they are not paths inside the frozen input tree. Full's
`run/analysis-policy.yaml` is the separately declared candidate policy, not a
permission to access raw private files. Match each advice artifact to the run's
recorded digest and recipient routing. The controller strategy is a separate,
independently hashed layer on top of the model research advice; do not concatenate
the files or route controller-only text to fixed workflow roles. No new human
advice is supplied during the clock. O-NoPrior must not acquire either advice
layer or dedicated analysis findings from another unit, inherited history or
recovery state.

The run must explicitly identify its condition, prior state and matching
artifacts. If they are missing, inconsistent or fail validation, report the
setup error before the affected operation; do not infer Full from nearby files.
Partial analysis-only or advice-only configurations are not supported.

## Narrow effect and remaining requirements

This decision resolves only the applicability of the common package's CLI
advice restrictions. Task science, data scope, training-pool requirements,
resource limits, continuing deadline, evaluator access and submission rules
retain their existing authorities. It grants no access to private targets or
evaluator implementation, changes no generic scheduling mechanism, and makes no claim
that a native executor has been provisioned.

The generic toolbox stays unchanged. A different task must bring its own
experiment declaration; it must not inherit this TIDMAD-specific interpretation.
Full policy/advice parity and actual execution still need qualification.

## NoPrior requires enforced information exclusion

A deployment must omit advice artifacts, dedicated analysis findings and Full
histories from every research-process-readable mount, inherited state and
recovery input. Do not expose the private exp checkout or operator output and
rely on instructions not to read it. Resume must preserve NoPrior's information
boundary. Validate it from the actual research process, including absolute-path
read attempts against existing prohibited artifacts.

The trusted execution route must also reject dedicated Data Analysis requests
for NoPrior and omit its findings from returned results. The current preparation
does not implement that execution route; setting an enablement field to false
is not evidence of enforced invocation denial. Generic documentation may describe
the existence of Data Analysis, but supplies neither prior content nor execution
authorization. Ordinary task-permitted reasoning/code is still allowed.
