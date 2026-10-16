# Planner request extraction qualification

## Scope and identity

Infra `3863dcc02cfe6c9fe06b8e991442d248ade3866e` extracts history observation, request
construction and planner invocation into a helper in the same module. Response
parsing remains in `prepare_attempt`. The producer remains included in the
rendering assembly fingerprint.
Request arguments and post-parse record construction retain their source
semantics. This qualification admits that exact assembly; it introduces no
historical renderer, execution algorithm or scientific configuration.

Use prompt package `0.10.15` and the existing v2 selection overlay in a fresh
historical workspace. Previous assembly entries remain admitted. Package source
identity changes intentionally; do not alter existing workspace identities to
resume in place. Frozen renderers, archives, task declarations, planner/runtime
packages, root pins and dependency locks remain unchanged.

## Offline validation

The receipt records 47 unchanged recovered request fixtures compared against
historical message hashes, installed-source/frozen-inventory checks and refusal
of unknown assemblies. The existing planner bridge self-check separately compares
28 historical synthetic message pairs and exercises registry compatibility.
The focused prompt-package and scheduler-manual tests verify the installed
historical profiles and their selection contracts.

This evidence covers rendered messages and the existing synthetic boundaries.
It does not establish complete conversation replay or identical future LLM
responses and training artifacts. Infra's focused request and record tests own
production helper reachability. No API calls, GPU work or dataset evaluation
are part of these checks.

## Reproduction

Install the four standalone compatibility packages into the exact candidate's
own frozen environment. Follow the existing
[capture procedure](../constraint-disclosure/report.md#reproduce-the-offline-checks)
for each unchanged fixture and v2 profile, using the revision above. Compare
receipt `messages` against the Luna-defaults receipt's `reference_messages`
without normalization. Run `check_installation.py --profile-version 2` and the
prompt-package tests plus `planner_compat/tests/test_scheduler_manual_v11.py`
with that Python and explicit `SIDERIUS_CHECKOUT`.

For the additional planner check, bind `paper-early-v2` using
`agent.prompt_rendering.bind_prompt_profile`, then call
`siderius_planner_compat.self_check.check()`. Provider requests are replaced by
an offline capture that checks the stored historical message hashes.

## Results

All 47 frozen request pairs match exactly; 66 focused tests pass without skips.
Installed-source and frozen inventory checks pass, including four unknown-assembly
refusals. All 28 planner message pairs match; two empty-registry cases and the
uncertain-registry refusal pass. `git diff --check` passes. No Python implementation
or frozen source changes are included in this companion.
