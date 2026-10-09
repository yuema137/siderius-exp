# Task-model-probe framework qualification

## Source and scope

Preflight compatibility 0.2.1 adds the source assembly at infra
`769bba4539cc9bef0189427d7da278da1012daac`. Existing qualification entries and
archived fixtures remain unchanged. Ordinary runs retain native estimation.
Explicit historical `static_only` with protected execution unselected is the
qualified compatibility scope; this does not expand measured/protected or
stochastic replay claims, or recover missing historical Project8 geometry.

[Source review](source-review.json) compares all 78 assembly members against the
already-qualified `b13b9263` source. Only the task composition projection,
TaskCompositionRef schema, and workflow setup-error handling changed. Static
arithmetic, batch search and observation owners are byte-identical. The new
candidate provider is unselected for the four paper tasks.

## Executed offline evidence

Using the exp checkout's own frozen environment and the selected clean infra
checkout's own environment:

- Before adding qualification metadata: `test_historical_estimation.py -k
  frozen_reference` passed all 45 phase-estimate and 32 batch-search cases.
- After installing the updated package: the four paper tutorial launch/config
  checks, planner setup, historical paper/manual and runtime-feedback checks,
  and preflight compatibility suite passed 164 checks. Three installation tests
  require the framework checkout environment; all three passed separately there.
- [Installation receipt](installation.json) verifies source/installed equality,
  selected-checkout assembly equality, parent/child identities, and rejection of
  unknown assemblies with normal provider discovery.
- The separate Cancer cohort passed 37 checks, covering packed-graph semantics,
  all candidate consumers, unchanged loader/split contracts and tutorial commands.

No API calls, GPU work, dataset downloads or training were performed. These
checks establish the stated deterministic behavior, not score or weight parity.

Adopting the new qualification changes the compatibility package identity.
Initialize a new workspace and retain old source/package pins for archived
workspaces; do not rewrite old locks or normalize away identity differences.
