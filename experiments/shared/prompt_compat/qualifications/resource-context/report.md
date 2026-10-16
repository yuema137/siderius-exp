# Planner resource-context qualification

## Scope

Native planner prompts now describe Trial without assuming sparse data or
normalized scores. The resource block distinguishes configured Trial/Formal
budgets from estimates belonging to the previous attempt. This changes native
presentation, not training, scoring, workload selection or budget enforcement.

Historical planner providers already own their system templates and user
renderers, including the old resource block. No additional old-policy function
is necessary. Bridge and planning documentation are included in the conservative
prompt assembly fingerprint, so the exact candidate still needs admission.

This qualification adds that admission to prompt package `0.10.13`, retaining
all previous assembly entries. Frozen source, fixtures, archives, task settings,
planner package, runtime package, root pins and locks are unchanged. Use the
updated historical overlay in a new workspace: planner assembly identity changes
when native planner source changes, even though historical messages are stable.
Do not rewrite an old workspace's expected identity to permit in-place resume.

## Evidence

The receipt records candidate `55c7c1aed512887a9c7a0c85d42453f0e402a2dd`, all
47 frozen request comparisons against the unchanged historical message hashes,
installed-source verification and unknown-assembly refusals. The existing bridge
self-check additionally compares 28 historical planner message pairs (12 current
legacy, six early legacy and ten composed-loss cases), exercises two empty
registry cases and rejects an uncertain old registry. These are synthetic branch
fixtures, separate from the recovered four-task rendering corpus.

The focused prompt-package and scheduler-manual suite checks the shared
historical boundary and configuration presentation. All checks are offline;
no model calls, training, dataset evaluation or archive mutation is involved.
Recovered message equality does not establish complete historical conversations
or identical future stochastic artifacts.

## Reproduce

Install the four standalone compatibility packages into the candidate's own
frozen environment. Use the existing `capture.py` procedure from
[the qualification instructions](../constraint-disclosure/report.md#reproduce-the-offline-checks)
for all fixtures and v2 profiles. Compare receipt `messages` with the immutable
Luna-defaults qualification's `reference_messages`, without normalization.
Run `check_installation.py --profile-version 2` and the prompt-package tests plus
`planner_compat/tests/test_scheduler_manual_v11.py` with the candidate Python.

For the additional planner check, bind `paper-early-v2` using
`agent.prompt_rendering.bind_prompt_profile`, then invoke
`siderius_planner_compat.self_check.check()`. The bound profile preserves the
separately qualified historical training-dynamics formatting. The check replaces
provider access with an offline capture and compares saved historical hashes.

All 47 frozen requests matched; all 50 focused tests passed without skips.
Installed source, frozen source inventory and four unknown-assembly refusals
passed. The 28 planner message pairs and three registry behavior checks passed.
Initial captures interrupted by candidate amendments were discarded; this receipt
contains only final committed-candidate evidence.
