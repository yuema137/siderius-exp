# Custom-loss target-contract qualification

## Paper execution audit

The retained execution records for the units identified in
[paper replay inventory](../../../planner_compat/paper-replay-369.json)
were inspected before selecting a compatibility strategy.

| Task and treatment | Retained run-output records | Recorded loss type |
|---|---:|---|
| TESS, no prior | 16 | `smooth_l1` |
| LIGO, no prior | 17 | `smooth_l1` |
| Project 8, no prior | 12 | `smooth_l1` |
| TIDMAD, no prior, four bands | 32 | `smooth_l1` |
| TIDMAD, analysis enabled, four bands | 32 | `smooth_l1` |

All `loss_type` declarations found recursively in these 109 retained JSON
records select the built-in objective. No generated loss modules were found
in those workspaces. The frozen prompt corpus contains eight model-implementor
fixtures for the four tasks and no loss-generation fixture. These findings cover
retained evidence; they do not establish that every discarded intermediate
request is recoverable.

The built-in objective does not route targets through custom-loss metadata.
Therefore this audit does not justify preserving the incorrect integer-target
conversion in an experiment plugin. The corrected custom-loss generation and
loading path remains normal framework behavior. The implementor module belongs
to the rendering assembly, so its changed source still requires explicit
assembly qualification and frozen-message comparison before historical profiles
can accept the candidate.

## Qualification boundary

No historical renderer, archived fixture, task meaning, root framework pin or
lockfile is changed. Source inspection and offline message comparisons establish
recovered input compatibility; they do not promise identical future LLM replies
or retrained artifact bytes. No API calls, GPU work or official-data scoring are
part of this qualification.

## Qualified source pair

Infra `367df3d478da5c9342de3a3cb7a4975aa9f51095` is paired with prompt
package `0.10.11` and runtime-verifier package `0.1.4`. The
[v2 scheduler-disabled overlay](../../profiles/paper-scheduler-disabled-v2.json)
records these package requirements for a fresh historical workspace. Its task,
workflow and planner selections are unchanged. Prior assemblies remain admitted;
prior qualification receipts and the v1 overlay are unchanged.

The runtime assembly also changes because training preparation and target
standardization now pass the expected custom-loss contract to target resolution.
Built-in loss handling and the historical timing algorithms are unchanged. The
runtime package adds only exact assembly admission; it does not modify its frozen
algorithms, adapter, finite-trace fixtures or original paper launch overlay.
The original incomplete prompt-only qualification correctly refused this unknown
runtime assembly in five planner tests; runtime qualification is required before
claiming the complete explicit historical selection works.

## Offline verification

The [receipt](receipt.json) records exact assembly and message identities.
The checks use the committed candidate's own frozen environment with the four
standalone compatibility packages installed normally. No source is injected
through `PYTHONPATH` and no archived fixture is rewritten.

- All 47 frozen rendering boundaries match the historical message hashes
  retained in the Luna-defaults receipt. These cover the four paper tasks and
  analysis-on boundaries, including eight model-implementor messages.
- Prompt installation checks compare installed source with this package and
  verify the frozen source inventory, including four unknown-assembly refusals.
- All 107 prompt, planner-v11 and runtime package tests pass without skips. They exercise scheduler-disabled
  historical presentation, original finite-trace measurements and admission,
  all three historical timing families, child identity validation and unknown
  runtime assembly refusal.
- Five explicit historical profile selections and the recovered analysis input
  identity are checked separately. Four archived task routing configurations
  retain their declared model routes.

## Reproduce

From the exp checkout, install `experiments/shared/{planner_compat,prompt_compat,
preflight_compat,runtime_compat}` into the selected infra checkout's own frozen
environment, following the [installation contract](../../usage.md). Then run:

```bash
SIDERIUS_CHECKOUT="$INFRA_CHECKOUT" "$INFRA_CHECKOUT/.venv/bin/python" -m pytest \
  experiments/shared/prompt_compat/tests \
  experiments/shared/planner_compat/tests/test_scheduler_manual_v11.py \
  experiments/shared/runtime_compat/tests -q
"$INFRA_CHECKOUT/.venv/bin/python" \
  experiments/shared/prompt_compat/check_installation.py --profile-version 2
"$INFRA_CHECKOUT/.venv/bin/python" \
  experiments/shared/prompt_compat/check_constraint_disclosure.py \
  --expected-revision 367df3d478da5c9342de3a3cb7a4975aa9f51095 \
  --selection experiments/shared/prompt_compat/profiles/paper-constraint-disclosure-v2.json \
  --output "$NEW_SELECTION_RECEIPT"
"$INFRA_CHECKOUT/.venv/bin/python" \
  experiments/shared/prompt_compat/check_paper_proposer_routing.py \
  --expected-revision 367df3d478da5c9342de3a3cb7a4975aa9f51095
```

For each unchanged `fixtures/*.json`, invoke the existing `capture.py` with this
candidate revision and corresponding v2 profile, using a fresh output directory.
Compare receipt `messages` to `reference_messages` in
`qualifications/luna-defaults/receipt.json`. The profile mapping and exact command
boundary are documented in the
[earlier reproduction instructions](../constraint-disclosure/report.md).
