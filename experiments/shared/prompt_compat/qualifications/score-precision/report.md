# Historical score precision

## Contract

Native training-dynamics, interpreter trajectory and planner resource values use the shortest
round-trip representation of the stored float, rather than a fixed decimal or
significant-digit limit. This changes text only; metrics, diagnosis derivation,
ranking, validity, training and saved records retain their numeric meaning.

The historical planner already owns its resource-block formatting.
The existing frozen training-dynamics renderer already preserves its historical
two-decimal text. A new generic `interpretation.score_value` boundary lets this
package preserve the historical four-decimal score expression for explicit
historical profiles. The expression and missing-score marker are extracted from
the source identified by `source-inventory.json`; they do not call the native
formatter. Early, late and analysis profiles reach this hook through the native
interpreter. The frozen TIDMAD interpreter already owns its old score expression.

## Selection

Prompt package `0.10.14` admits the exact candidate recorded in the receipt.
Use the existing v2 selection overlay in a fresh historical workspace. Previous
assembly entries remain admitted. Package source identity changes intentionally;
do not rewrite identities in existing workspace locks to continue in place.
Frozen archives, scientific settings, original templates, root installation pins
and dependency locks are unchanged. No historical training or scoring algorithm
is introduced.

## Verification boundary

Qualification compares all 47 unchanged recovered request fixtures against the
previously recorded historical hashes. Tests cover explicit historical score
selection and native restoration outside its scope, tiny positive/negative
scores, zero and missing scores. Existing shared training-dynamics tests cover
its independently frozen rendering. Installed-source checks validate source
inventory and reject unqualified assemblies.

These are offline message and selection checks, not a claim that stochastic LLM
responses or retrained artifact bytes repeat. No API calls, GPU work, datasets or
private test labels are needed.

To reproduce, install the four standalone compatibility packages into the exact
candidate's own frozen environment. Use `capture.py` with each unchanged fixture,
the recorded revision and the corresponding v2 profile, following
[the qualification procedure](../constraint-disclosure/report.md#reproduce-the-offline-checks).
Run `check_installation.py --profile-version 2` and the prompt-package tests plus
`planner_compat/tests/test_scheduler_manual_v11.py` with that same Python and an
explicit `SIDERIUS_CHECKOUT`. Compare message hashes without normalization.

## Verified pair

Infra `23533342ce4257797fa5bdb915f4c303c6ca9ff0` with prompt package
`0.10.14`: all 47 frozen requests match and all 66 focused tests pass without
skips. Installed-source inventory and four unknown-assembly refusals pass.
The existing planner self-check, with `paper-early-v2` bound, also matches all
28 historical message pairs and passes its two empty-registry cases and uncertain
registry refusal. Ruff check, format check on authored Python and diff check pass.
