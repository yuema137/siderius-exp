# Historical constraint-disclosure selection

For the scheduler-capable framework, use the newer explicit
[scheduler-disabled selection](scheduler-disabled.md), which also retains the
constraint-disclosure choices documented here.

## Scope and ownership

New framework workflows disclose existing task and workflow restrictions to
agents throughout the workflow. Normal runs retain this default. The explicit historical
selection in [paper-constraint-disclosure-v2.json](profiles/paper-constraint-disclosure-v2.json)
combines a paper prompt renderer with `disclose_execution_constraints: false`.
It suppresses the newly added advisory context, not parameter-rule enforcement,
objective selection, resource checks, or recorded execution provenance.

The standalone `siderius-prompt-compat` package owns historical rendering. Its
`constraints.disclosure` override returns an empty string for absent context
and rejects populated context with the required workflow selection. The workflow option
also keeps the new context out of historical Data Analysis inputs. This matters
because analysis plans must echo the canonical input identity: removing context
only from the prompt would produce an identity that execution rejects.

This selection preserves existing historical restrictions; it does not grant an
agent permission to change locked values. Unknown renderer assemblies still
fail closed. A changed compatibility package has a new identity: use a new
workspace and preserve old package installations, run locks, and archives.

## Apply to an external historical project

For the complete disclosure path, use package `0.10.8` and framework
`3adaa9871b66382401a8cec8010f605fe950d275`, qualified in the
[downstream report](qualifications/downstream-constraints/report.md);
the repository root installation pin is unchanged and does not gain this option.
Install this standalone package into that framework checkout's own frozen
environment using the [existing installation procedure](usage.md#1-install-into-the-infra-environment).

For the selected case, apply `task_composition_overlay` to the copied task
manifest and `workflow_launch_overlay` to the copied workflow configuration.
Preserve the original task semantics, data, budgets and separately selected
planner/runtime policies. The overlay is a selection reference, not a launcher.
Do not change archived task manifests or old workspaces.

The standard workflow command must include:

```bash
--no-disclose_execution_constraints
```

For the native Python API, the equivalent launch setting is:

```python
WorkflowLaunchConfig(..., disclose_execution_constraints=False)
```

The copied task manifest must also select the corresponding `paper-*-v2`
`prompt_renderer` listed in the overlay. Both selections are required: disabling
context transport alone does not select historical text, and selecting the
renderer alone does not preserve a populated Data Analysis input identity.
The framework records the launch setting in run identity; do not bypass a
resume mismatch by editing an existing lock.

## Offline checks and limits

`check_constraint_disclosure.py` loads the five explicit task/profile selections
(four paper tasks and the separate TIDMAD analysis-on branch), exercises native
workflow projection and checks that deterministic exact rules still resolve.
These are synthetic profile-selection witnesses, not full task-composition
loads or workflow executions. The separate frozen request corpus supplies
recovered inputs from the four paper tasks. The identity witness also carries a recovered analysis brief through the interpreter-to-analysis
adapter and validates the identity from the historical plan prompt using a
synthetic, non-executing plan. It neither calls a provider nor reads a dataset.

Run this in the qualified framework environment with its exact committed
revision and a new output file:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_constraint_disclosure.py" \
  --expected-revision "$INFRA_REVISION" \
  --selection "$EXP_CHECKOUT/experiments/shared/prompt_compat/profiles/paper-constraint-disclosure-v2.json" \
  --output "$NEW_RECEIPT_PATH"
```

The separate frozen-request comparisons establish equality only for their
recorded boundaries and inputs. They do not establish complete conversation
replay, identical future model responses, or equal retrained scientific scores.

## Earlier upstream-only qualification

Package `0.10.7`, framework `35be68663787ddd03411651c36bee71c57a0043f`, and
[selection v1](profiles/paper-constraint-disclosure-v1.json) retain their separate
[upstream report](qualifications/constraint-disclosure/report.md). That earlier
pair does not include downstream disclosure. Its archived evidence remains
unchanged; new complete-path selections use the qualified pair above.
