# Historical scheduler-disabled workspaces

## Scope and ownership

The current native framework supports explicit learning-rate schedules. Paper
runs predate that feature. Select the experiment-owned
[overlay](profiles/paper-scheduler-disabled-v2.json) in a **new workspace** to
retain the qualified historical training conditions and prompt presentation.
The pre-L3 scheduler-disabled reference is documented in the
[pre-L3 qualification report](qualifications/pre-l3-scheduler-disabled/report.md);
the current L3 candidate has a separate [#908 qualification report](qualifications/l3-908/report.md).
Each report binds one exact framework revision and offline evidence. Later
framework revisions require their own exact qualification entries and receipts.
The root repository dependency pin and original archived workspaces remain
unchanged; this overlay requires the separately qualified framework and package
versions in its `required_packages` mapping.

Merge the selected case's `task_composition_overlay` into a copied task
composition, and its `workflow_launch_overlay` into the launch configuration.
Merge `workflow_parameter_rules` by parameter path; retain all existing task and
workflow rules, epoch limits, data restrictions and resource budgets. If an
existing scheduler rule conflicts with `train_config.lr_schedule: {exact: null}`,
stop and resolve the explicit historical selection rather than discarding a
rule. Set the tuning role's `planner_strategy` to the case's versioned v11
selector. Install all four standalone compatibility packages into the exact
framework environment before resolving identities; do not resume old locks.

## Execution and presentation are separate

Native `ParameterRules` resolves the proposed baseline and tuning configuration.
The exact-null rule disables scheduling even when a proposed candidate requests
it. No historical renderer changes a configuration or optimizer. The display
projection removes only that verified exact-null compatibility rule from the
old prose and preserves every other task/workflow rule. Nested scheduler rules,
non-null values and other scheduler restrictions are refused by the historical
presentation. The unchanged original rule object still governs execution.

Selecting only a renderer is **not** an execution admission policy. A standalone
renderer may render an old input with no scheduler field; only the complete
explicit overlay supplies the new execution lock. Do not use historical prose
as a way to run an enabled scheduler. The v11 planner additionally refuses
non-null scheduler evidence in effective/proposed record configurations or
recorded learning-rate histories.

The v11 manual projection accepts the exact qualified current configuration
manual and renders the previously frozen early/late paper manual. Unrelated
schema changes fail rather than being silently removed. The newly qualified
assembly uses an exp-owned pre-scheduler native-training appendix where the
historical branch included one. Previously admitted assemblies retain their
previous appendix dispatch. Earlier paper branches that omitted the appendix
continue to omit it.

## Verification boundary

The scheduler qualification combines actual current-manual comparisons,
explicit overlay → native baseline resolution → historical rule presentation,
frozen paper message boundaries, synthetic complete proposer/reflector requests
and repair-helper text. The preflight estimator and runtime verifier retain
unchanged historical algorithms, qualified against their new source closures.
No API, GPU or training run is required. These checks do not promise identical
future LLM replies or retrained model bytes; original scientific artifacts and
source revisions remain separately preserved.
