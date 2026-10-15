# Optional analysis brief receipt qualification

## Pair and scope

Infra `e7549a3bfa98d3c5ec77ae0a39d1b99e3a82c400` fixes #723 by recording
an optional analysis brief's resolved execution model, including defaults.
Prompt compatibility package `0.10.10` admits that exact rendering assembly.
Use the [v2 scheduler-disabled overlay](../../profiles/paper-scheduler-disabled-v2.json)
in a new historical workspace. Its scientific and workflow settings match v1;
only the required prompt package version changes.

Source inspection confirms that the infra change adds receipt-route resolution;
message construction, provider calls, proposer and reflector rendering are
unchanged. The assembly remains classified as scheduler-disabled so historical
appendix and parameter-rule presentation retain the prior qualified behavior.
All previous qualification entries, the v1 overlay, archived inputs, renderers,
root infra pin and lock are preserved.

## Offline evidence

The [receipt](receipt.json) records the exact assembly and message identities.

- All 47 frozen boundaries match the reference message hashes preserved in the
  Luna-defaults qualification. Inputs cover the four paper tasks and analysis-on
  boundaries; no original fixtures were rewritten.
- 42 prompt-package and v11 tests pass, including actual baseline resolution
  with both scheduler overlays and rejection of unknown or enabled scheduling.
  The assembly-dispatch test now checks every qualified assembly by its explicit
  classification, avoiding an assumption about list order.
- 19 affected analysis-brief tests pass, covering defaults, explicit models,
  invalid-response and timeout receipts, resume identity and prompt stability.
- Installed package verification passes with four unknown-assembly refusals.
  Five historical disclosure mappings and the analysis input identity pass;
  this checker uses its own disclosure overlay. Scheduler-overlay enforcement
  is established by the separate baseline-resolution tests above.
- Four archived task routing configurations pass the existing routing check.

No API, GPU, dataset, training or inference execution occurred. Full proposer
and reflector captures were not repeated because their source and message
construction did not change. This evidence establishes recovered prompt
boundaries, not identical future LLM replies or retrained artifact bytes.

## Reproduction

Use the candidate checkout's own frozen environment; install the four standalone
compatibility packages there. Keep the root exp environment and pins unchanged.
From the exp checkout, run:

```bash
SIDERIUS_CHECKOUT="$INFRA_CHECKOUT" "$INFRA_CHECKOUT/.venv/bin/python" -m pytest \
  experiments/shared/prompt_compat/tests \
  experiments/shared/planner_compat/tests/test_scheduler_manual_v11.py -q
"$INFRA_CHECKOUT/.venv/bin/python" -m pytest \
  "$INFRA_CHECKOUT/tests/unit/agent/result_interpretation_agent/test_analysis_brief_generation.py" \
  "$INFRA_CHECKOUT/tests/unit/agent/result_interpretation_agent/test_analysis_brief_route.py" -q
"$INFRA_CHECKOUT/.venv/bin/python" \
  experiments/shared/prompt_compat/check_installation.py --profile-version 2
```

For each unchanged `fixtures/*.json`, invoke the existing `capture.py` with this
candidate revision and matching v2 profile. Compare receipt message hashes to
`reference_messages` in `qualifications/luna-defaults/receipt.json`, as documented
in the [upstream reproduction instructions](../constraint-disclosure/report.md).
Use fresh output directories. Run `check_constraint_disclosure.py` with
`profiles/paper-constraint-disclosure-v2.json`, and the existing
`check_paper_proposer_routing.py`, both with this exact candidate revision.
