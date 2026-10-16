# Historical training-dynamics precision

## Contract

Native infra renders training-dynamics floating values using six significant
digits, including signed train/validation gaps. Explicit historical prompt
profiles retain the former two-decimal text through `tuner.training_dynamics`.
The framework owns the generic rendering boundary; this package owns the old
presentation. This does not change recorded numbers, diagnosis derivation,
training, scoring, resource admission or retry behavior.

The frozen function and its private formatter are extracted from the source
identified in `source-inventory.json`. They do not call the native formatter.
Both legacy planner wrappers and historical interpreter renderers reach the
shared boundary, so this preserves their old text without copying additional
orchestration logic. The frozen source retains its original formatting.

## Selection and identity

Use prompt package `0.10.12` with the qualified candidate and the existing v2
profile selection in a fresh workspace. Existing qualifications remain admitted;
new package contents intentionally have a different source identity. Do not
replace package identities inside an old workspace or rewrite archived prompts.
The current scheduler-disabled overlay declares the new package requirement;
its scientific settings, task/profile mappings and planner choices are unchanged.
Root framework pins and dependency locks are unchanged.

## Offline qualification

The accompanying receipt identifies the exact source pair and compares all 47
unchanged frozen request fixtures with the historical message identities in the
Luna-defaults qualification. Focused tests cover shared planner, reflector and
interpreter callers, small positive/negative gaps, absent evidence and invalid
evidence. Installation validation checks frozen source inventory and refusal of
unknown assemblies. These are recovered message-boundary checks, not complete
historical conversations, identical future LLM responses or retrained artifacts.
No provider requests, data evaluation or GPU work are needed.

Follow the capture commands in
[the qualification procedure](../constraint-disclosure/report.md#reproduce-the-offline-checks),
using the exact candidate revision in this receipt and `--profile-version 2`.
Install all four standalone compatibility packages into that candidate's own
frozen environment first. Run `check_installation.py --profile-version 2`, the
prompt compatibility tests, and `test_scheduler_manual_v11.py` with the same
Python and an explicit `SIDERIUS_CHECKOUT`. Never supply source via `PYTHONPATH`.

## Verified pair

Infra `7e83451ff7632d5c4ee2e338c8847cd3321c3bc4` with prompt package
`0.10.12`: 47/47 frozen requests match exactly; all 50 focused tests pass
without skips. Installed package source and 15 frozen source entries were
verified, including four unknown-assembly refusals. Ruff check passes for
changed Python; format check covers authored files while the extracted historical
function retains source formatting. `git diff --check` passes.
