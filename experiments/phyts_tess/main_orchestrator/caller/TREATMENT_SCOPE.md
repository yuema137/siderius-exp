# PhyTS TESS orchestrator information-treatment scope

Operator decision: 2026-09-22. This is an additive experiment declaration for
the orchestrated condition **O-NoPrior**, not a change to the frozen task or
the generic toolkit. Read it together with `SIDERIUS-RUN.md` in the assembled
agent workspace.

## The contrast this condition belongs to

The fixed-workflow arms in `experiments/phyts_tess/information_treatments/`
hold the task, data, metric, validity rules and workflow parameters fixed and
vary only the information given to the research agent. The orchestrated
condition holds the same task, data, metric, validity rules and per-attempt
execution bounds fixed and varies the **control structure**: an external
caller selects and sequences SIDERIUS capabilities itself instead of
following the fixed chain.

So that this is a one-variable change against the fixed no-prior arm, the
orchestrated condition inherits that arm's information state exactly:

| declared treatment | advice | Data Analysis | Literature review |
| --- | --- | --- | --- |
| `phyts-tess-main-fixed-no-prior-v1` (fixed workflow, `nop_004`) | disabled | disabled | disabled |
| **O-NoPrior** (this condition) | absent | disabled, no findings injection | disabled |

Literature review is disabled because it is disabled in the fixed arm, not
as a judgement about its value: enabling it here would make the comparison a
two-variable change. The framework refuses a literature-review launch
without a task-owned configuration anyway; none exists for this task.

## What "no prior" enforces

- No `advice.json`, no controller strategy artifact, no analysis findings
  and no other run's history are present in any path the research process
  can read. Their absence is expected and is not a setup error.
- The dedicated Data Analysis capability is not bound; a request for it is
  a setup error to report, not a capability to work around through another
  input field, a cache or a prior workspace.
- The published task package carries the benchmark's own reference points
  inside its `task_description`. That is task content available to every
  condition, not an advice artifact, and it is not to be removed or
  paraphrased into one.
- Ordinary task-permitted reasoning and code are allowed.

## Narrow effect and remaining requirements

This decision resolves only which information state the orchestrated
condition carries. Task science, data scope, execution bounds, the six-hour
clock, evaluator access and the candidate contract retain their existing
authorities (`SIDERIUS-RUN.md` names each). It grants no access to
validation targets or the evaluator implementation and changes no generic
scheduling mechanism.

A different task must bring its own declaration; this one is TESS-specific
and must not be inherited.
