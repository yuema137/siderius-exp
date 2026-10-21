# Observation timestamp qualification

## Qualified boundary

Infra `a366edba08b0b8a89bd30137f7535e81f4a11da9` corrects native offset
interpretation. Standalone `siderius-runtime-compat` 0.1.5 explicitly retains the
original local-clock parser for the three historical verifier families covering
TESS, LIGO, Project8 and TIDMAD. The package sources and final infra assembly are
bound by the existing provider identity. New identities require fresh workspaces.

This is a standalone package/framework qualification, not a root dependency
upgrade: the exp root framework pin and frozen lock remain unchanged. Install the
package in each environment actually running the paired infra. Installing the
exp root environment alone does not activate this package or establish this pair.

## Executed evidence

The unchanged original `_age_seconds` function was extracted with `git show`
from each of the three revisions recorded in
`../../fixtures/observation-timestamps.json`, then executed in independent
subprocesses with UTC, America/Los_Angeles and Asia/Shanghai. The fixture preserves
source text, source identities and outputs; it is not generated from the new
parser. The packaged parser matches all outputs, including equivalent-offset,
naive and malformed inputs.

The focused suite passed 116 tests on the qualified infra:

```sh
"$SIDERIUS_CHECKOUT/.venv/bin/python" -m pytest \
  experiments/shared/runtime_compat/tests \
  experiments/shared/planner_compat/tests/test_runtime_verifier_v8.py -q
```

Execute from this exp checkout after a normal, noneditable installation of its
standalone runtime (0.1.5), planner (0.12.1) and preflight compatibility packages into that exact
infra environment. The infra environment itself is created using its frozen lock.
No `PYTHONPATH` override or borrowed virtualenv is used.

New tests populate an eligible observation store, compare native and historical
expiry before/at/after the native 90-day boundary, and consume the historical
prior through the production runtime session and its selected frozen verifier.
Verifier feed states, complete measurements and predictions match the direct
original implementation supplied with the independently computed historical prior. The unchanged bare preflight key
cannot match provider-labelled records. Existing tests additionally verify all
23 preserved finite-workload session outcomes, original verifier branch outputs,
installed child identity, refusal of unqualified assemblies, paper launch overlays
and historical planner presentation. Ruff and diff whitespace checks passed.

## Limits

The historical parser remains host-timezone dependent; replay needs the same
host timezone. Clean historical workspaces are supported; importing unrelated
native observations is not qualified. Sorting and drift ordering remain unchanged
and are tracked separately in infra #766. Fractional-offset formats outside the
native writer's whole-second timestamp format are tracked in infra #767.

These offline checks establish the bounded timing decisions and existing prompt
projection, not regenerated model weights, predictions, scores or stochastic LLM
responses. No API calls, GPU work or dataset access occurred. Archived fixtures,
launches and prior receipts remain unchanged.
