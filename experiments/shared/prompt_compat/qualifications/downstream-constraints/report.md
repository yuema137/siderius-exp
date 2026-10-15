# Downstream constraint-disclosure qualification

## Qualified pair and scope

Infra: `3adaa9871b66382401a8cec8010f605fe950d275`.
Exp base: `9ca46d1cc6354eb0c43412e609ba3859364e9488`.
Standalone prompt-compat package: `0.10.8`.

This qualification extends the existing explicit historical selection to the
proposer, implementor, validator, planner and reflector disclosure paths. It
adds a v2 renderer-assembly entry and a new selection overlay; no historical
renderer code, original fixtures, archived task configurations, root infra pin
or dependency lock changes. Package 0.10.7 and its upstream receipt remain
separately recorded.

Historical selection still requires both the matching paper renderer and
`disclose_execution_constraints=False`. Ordinary workflows retain disclosure;
all original deterministic restrictions remain enforced in either mode. See
[the current selection contract](../../constraint-disclosure.md).

## Executed evidence

The [receipt](receipt.json) contains the exact source, package, fixture and
message identities. All final checks used the clean committed infra revision
and normal installed profile loader, with no profile-admission patches.

| Check | Result | What it establishes |
| --- | --- | --- |
| Frozen paper request corpus | 47/47 message-hash matches | Recovered four-task and analysis-on inputs at declared rendering boundaries |
| Proposer | 48/48 sequences, 156/156 complete requests match | Native node orchestration and retries with scripted provider replies |
| Reflector | 20/20 complete requests match | Actual `LLMBridge.reflect` requests across four task/metric inputs and five synthetic provenance cases |
| Implementor repair | 8/8 complete user strings match | Repair renderer helpers with recovered inputs and synthetic code/error history; not native implementor retry loops |
| Historical selection | Five mappings pass | Explicit workflow opt-out and retained exact-rule enforcement |
| Analysis input identity | Pass | Native interpreter adapter preserves input; native plan validation accepts the historical prompt identity |
| Package tests | 30 passed, none skipped | Profile refusal, historical view guards, recovery and comparator regressions |
| Installation and routing | Pass | 16 installed source files, 13 frozen source entries, four unknown-assembly refusals, four paper routing configurations |

The 47-case comparison uses historical reference message hashes retained in the
[earlier corpus receipt](../luna-defaults/receipt.json), not rerun original paper
checkouts. The existing frozen fixtures are unchanged.

Proposer, reflector and repair supplementary comparisons execute clean
reference `c7996a352d064229725ab1ebe886b9006bdbf36d` and the candidate in their own
frozen environments. Proposer uses explicit v1 profiles on the reference and v2
on the candidate. Reflector uses the reference's native plan-only provenance
and the candidate's explicit historical presentation, while retaining current
execution evidence. Repair compares the unchanged helper strings without a
provider call. Full strings are compared before compact identities are saved.

These are synthetic branch witnesses, not recovered historical conversations.
No API, GPU, training, inference or dataset operations occurred. Equality of
future LLM replies, retrained models or complete paper artifact bytes is not
claimed. Native actual-call tests in the paired infra change separately cover
constraint delivery to model/loss generation and repairs, proposal corrections,
validator review, planner and reflector; those tests do not turn the helper
comparisons here into historical end-to-end execution evidence.

## Reproduction

Use each checkout's own frozen environment and normally install the selected
standalone package. The reference used prompt-compat 0.10.7; the candidate used
0.10.8. Their different package identities are explicit. Keep outputs in fresh
external directories and preserve existing workspace locks.

Run the commands in the [upstream report](../constraint-disclosure/report.md)
with the candidate revision above. For `check_constraint_disclosure.py`, select
`profiles/paper-constraint-disclosure-v2.json` using its `--selection` option.
The unchanged proposer comparator binds the reference to its exact revision.

For each of `tess`, `ligo`, `project8` and `tidmad`, run the existing reflector
capture in the reference without `--profile`, then in the candidate with its
matching v2 renderer. Compare the five system/user pairs byte for byte:

```bash
"$BASE_INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/capture_reflector.py" \
  --case "$TASK" --expected-revision c7996a352d064229725ab1ebe886b9006bdbf36d \
  --output "$NEW_REFERENCE_OUTPUT"
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/capture_reflector.py" \
  --case "$TASK" --expected-revision 3adaa9871b66382401a8cec8010f605fe950d275 \
  --profile "$PAPER_V2_PROFILE" --output "$NEW_CANDIDATE_OUTPUT"
```

Run `qualifications/probe-contract/capture_repair.py` once per checkout with
`--fixtures` pointing to the unchanged fixture directory, `--revision` naming
the exact checkout revision, and distinct `--output` directories. Compare its
eight text files. This command captures only repair user rendering.

Changed Python passed Ruff check and format check. `git diff --check` passed.
The new assembly is admitted only to the v2 allowlist; unknown assemblies and
populated context under a historical profile remain explicit errors.
