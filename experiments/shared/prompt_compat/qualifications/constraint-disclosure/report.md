# Upstream constraint-disclosure qualification

## Source pair and result

Candidate infra: `35be68663787ddd03411651c36bee71c57a0043f` (upstream #721 change).
Exp source base: `f907517`; standalone prompt-compat package: `0.10.7`.
The [receipt](receipt.json) records the installed profile source identities and
capture-tool identities. No archived fixture, historical renderer, task source,
root infra dependency pin or dependency lock changed.

| Check | Result |
| --- | --- |
| Four-task and analysis-on frozen rendering corpus | 47/47 exact message-hash matches |
| Full synthetic proposer request comparisons | 48/48 sequences, 156/156 requests match |
| Explicit historical selection | Five profile mappings pass |
| Recovered analysis input through native protocol adapter | Unchanged serialized input; prompt identity accepted by native plan validation |
| Installed package and source inventory | 16 files, 13 frozen source entries checked; four unknown-assembly refusals |
| Explicit paper proposer routing | Four task configurations match their declared routes |
| Package tests against candidate infra | 30 passed, none skipped |
| API / training / GPU operations | None |

The frozen corpus compares candidate message hashes against the historical
reference hashes retained in the [previous qualification](../luna-defaults/receipt.json).
It does not rerun those old historical checkouts. The four-task proposer check
separately executes the existing synthetic requests in clean reference
`c7996a352d064229725ab1ebe886b9006bdbf36d` and the candidate, each using its own
frozen environment. Full system/user strings are compared before compact hashes
are recorded. The fixtures and reference renderers are unchanged.

The selection witness exercises native workflow projection with each declared
profile mapping and a synthetic exact epoch rule. It does not load all task
compositions or run workflows. The analysis identity check uses the recovered
analysis-plan fixture, the native interpreter-to-analysis adapter, and a
synthetic plan with no invocations. This proves the historical prompt requests
a valid current input identity without executing data or a program.

These checks establish the bounded messages and selection contracts above.
They do not prove complete historical conversation replay, identical future
LLM replies, equality of retrained scores, or all paper artifact bytes.
The downstream part of #721 and scheduler support are not covered by this PR.

## Explicit historical selection

Follow [the selection contract](../../constraint-disclosure.md). New workflows
keep native disclosure enabled. Historical workflows explicitly disable the new
advisory transport and select the matching experiment-owned renderer. Existing
parameter rules, objectives and resource checks remain enforced. Selecting a
historical renderer with populated new context fails clearly rather than
silently presenting a different Data Analysis identity.

Only the candidate assembly is added to the v2 allowlist. V1 is not newly
qualified. Both old and new workspaces retain their source and package identity;
use a fresh workspace for this package. The repository root installation pin
remains unchanged and does not imply support for the new launch option.

## Reproduce the offline checks

Install the standalone package into the candidate and reference checkout's own
frozen environments. Set `INFRA_CHECKOUT`, `BASE_INFRA_CHECKOUT` and `EXP_CHECKOUT`
explicitly; use fresh output paths for every command.

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_constraint_disclosure.py" \
  --expected-revision 35be68663787ddd03411651c36bee71c57a0043f \
  --output "$NEW_SELECTION_RECEIPT"
"$EXP_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/compare_proposer_requests.py" \
  --reference "$BASE_INFRA_CHECKOUT" --candidate "$INFRA_CHECKOUT" \
  --output "$NEW_PROPOSER_OUTPUT"
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_installation.py" \
  --profile-version 2
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_paper_proposer_routing.py" \
  --expected-revision 35be68663787ddd03411651c36bee71c57a0043f
SIDERIUS_CHECKOUT="$INFRA_CHECKOUT" "$INFRA_CHECKOUT/.venv/bin/python" \
  -m pytest "$EXP_CHECKOUT/experiments/shared/prompt_compat/tests" -q
```

For the frozen corpus, use existing `capture.py` on each unchanged `fixtures/*.json`
with the candidate revision and corresponding v2 profile, then compare each
receipt's `messages` hashes to `reference_messages` in the previous qualification.
The mapping remains TESS/LIGO → early, Project8 → late, TIDMAD → tidmad-noprior,
and analysis → analysis-c0467447. Alternatively, the existing `compare.py` can
rerun historical references when all explicitly pinned reference checkouts are
available. Neither path normalizes whitespace or edits expected messages.

Changed Python files passed Ruff check and format check; `git diff --check`
passed. Initial diagnostic captures used provisional profile admission only to
find incompatibilities before source freeze; none are included in this receipt.
All recorded final captures used the normal installed profile loader and the
clean committed candidate.
