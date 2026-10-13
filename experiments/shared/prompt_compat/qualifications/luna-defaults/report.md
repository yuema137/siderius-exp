# Central model-default qualification

## Scope and result

Infra `141ce44787ba1cf3e210a583dc8991d21168f0ad` changes omitted model routing to
OpenAI GPT-5.6 Luna. The four paper experiment configurations explicitly select
OpenAI GPT-5.6 Sol with medium reasoning for all eleven routes, including each
proposer, tuner and literature substage. Their explicit settings remain intact.
No historical configuration, renderer, fixture or repository dependency pin is
changed by this qualification.

The [receipt](receipt.json) records 47 matching frozen rendering requests, eight
matching supplementary repair messages, four matching historical proposer
routing checks and installed-package verification. The package suite passed
21 tests; all four v2 profiles still reject an unknown assembly. These checks
used no provider, GPU or training calls. They establish message and routing
compatibility within the stated coverage, not identical future model responses,
full conversation replay or reproduction of scientific scores.

The repair differential uses the preserved capture at infra
`a50c578a9b975f301122e65dfee11101cd83ba72`, qualified in the
[probe-contract report](../probe-contract/report.md). These eight requests use
recovered task inputs with synthetic candidate code and error history. They do
not represent eight recovered historical repair conversations.

## Identity and installation

Node and schema default declarations are inside the framework's conservative
rendering source inventory. Their changed source therefore needs qualification
even though these explicitly configured historical messages do not change.
Prompt-compat 0.10.6 adds the candidate assembly only to the v2 allowlist; v1
qualifications and frozen renderers remain unchanged.

Install this package in the candidate infra checkout's own frozen environment.
A changed package changes recorded profile identity: use a new workspace and
preserve old environments, locks and archives. This qualification does not
change the repository-wide installation pin or authorize a launch.

## Offline reproduction

Use the [existing comparison procedure](../../usage.md#3-inspect-the-offline-comparisons)
with `--profile-version 2` and the candidate revision above. Historical reference
checkouts must match the revisions declared by the unchanged fixtures.

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/compare.py" \
  --candidate "$INFRA_CHECKOUT" --references "$REFERENCES_JSON" \
  --profile-version 2 --output "$NEW_OUTPUT_DIRECTORY"
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_paper_proposer_routing.py" \
  --expected-revision 141ce44787ba1cf3e210a583dc8991d21168f0ad
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_installation.py" \
  --profile-version 2
SIDERIUS_CHECKOUT="$INFRA_CHECKOUT" "$INFRA_CHECKOUT/.venv/bin/python" \
  -m pytest "$EXP_CHECKOUT/experiments/shared/prompt_compat/tests" -q
```

For the supplementary repair differential, run the unchanged
[repair capture script](../probe-contract/capture_repair.py) against the pre-change
and candidate revisions, using separate new output directories, and compare the
eight corresponding text files byte for byte. Its CLI and environment checks
are documented in the probe-contract report. No original datasets are required.
