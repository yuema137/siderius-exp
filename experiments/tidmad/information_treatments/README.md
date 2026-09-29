# TIDMAD information treatments

These small files say what information an experiment gives to its research
agent. They do not change the TIDMAD task, data, metric, or validity rules.

## Current fixed-workflow files

| File | Advice | Data Analysis | Literature Review | Used by |
| --- | --- | --- | --- | --- |
| `main-fixed-no-prior.yaml` | Off | Off | On | fixed NoPrior workflow |
| `main-fixed-da-only.yaml` | Off | On | On | fixed DA-only ablation |
| `main-fixed-full.yaml` | On, `full-prior-v8/advice.json` | On | On | fixed Full workflow |

The YAML file is the switchboard for information exposure. The shared task
composition and `workflow.json` stay the same across these rows. Advice is an
explicit artifact with a SHA-256 when enabled; an advice-off row records
`mode: disabled` and no artifact. Module states are explicit so a missing key
cannot silently turn Data Analysis on or off.

The older `prerelease-with-advice.yaml` and
`prerelease-without-advice.yaml` files describe an earlier qualification
surface. Keep them for historical reproduction; do not use them as the current
ICLR fixed-workflow treatment.

Both treatments use the same task package in `tasks/tidmad`:

- `prerelease-with-advice.yaml` includes the reviewed prerelease advice file.
- `prerelease-without-advice.yaml` explicitly includes no human advice.

The launch adapter resolves one of these files before doing any work. When
advice is enabled, its checksum is checked before launch. When it is disabled,
the absence is recorded instead of being left implicit.

Module states are also explicit. For example, literature review can be turned
off in a SIDERIUS workflow while being `not_applicable` to a coding-agent
product that has no matching workflow module.

## How a treatment is called

The fixed-workflow preflight resolves the selected treatment before building
the SIDERIUS command. It records the treatment id, artifact digest, and module
states in the launch receipt. Users normally select the treatment through the
fixed workflow's launcher binding; they should not edit the generated command
to add or remove an advice/data-analysis flag. To create a new condition, add a
new treatment file and qualify it against the same task composition.

For the main fixed workflow, `main-fixed-no-prior.yaml` declares Data Analysis
disabled. The SIDERIUS adapter renders this as `--no-data_analysis_enabled`;
an enabled state renders `--data_analysis_enabled`. Both flags are derived from
the existing `modules.data_analysis.siderius` treatment field, not from a
second experiment switch. An enabled main-workflow treatment remains
non-launchable until the experiment provides a qualified band-scoped analysis
binding.

`main-fixed-da-only.yaml` enables Data Analysis and literature review while
explicitly disabling model advice. Prepare and launch with `--condition da-only`;
see [the fixed-workflow launch guide](../main_fixed_workflow/FULL_LAUNCH.md).
The completed NoPrior runs are the reused controls; the new treatment does not
schedule replacement controls or change the frozen task package.

## Strategy-only advice for the next orchestration runs

[Controller work strategy V3](controller-work-strategy-v3.md) contains only
research organization, adaptive resource use and completion guidance. It has
no model architecture, capacity, loss or task-specific training recipe.
The strategy-on condition disables model advice and Data Analysis;
the completed strategy-off runs are reused as controls.

The orchestrator preparation command binds V3 through `--strategy-only`;
see [the deployment contract](../main_orchestrator/STRATEGY_ONLY.md).
The legacy Full selector and controller V2 below do not implement this condition.
Keep historical artifacts unchanged for provenance; do not launch the legacy
Full condition as a substitute for strategy-only advice.

## Historical frozen Full V8

`main-fixed-full.yaml` now binds the frozen English V8 advice. The shared
[manifest and four band policies](full-prior-v8/README.md) are the common prior
authority for fixed workflow and orchestration. DA has a 600-second allowance;
NoPrior continues to disable advice and DA explicitly. The preparation CLI
materializes verified deployment inputs without starting a run.
