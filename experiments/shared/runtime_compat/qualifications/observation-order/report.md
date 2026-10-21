# Observation chronology qualification

## Qualified pair and behavior

Infra `7b0ab06f0a4d2e205725a7d778443202280ac02b` fixes chronological ordering
and fractional UTC offset parsing for native observation lookup. Standalone
`siderius-runtime-compat` 0.1.6 explicitly preserves the original local-clock
parser and lexical timestamp order. Planner package 0.12.2 declares this runtime
package as its optional historical-runtime dependency. The existing early/late
scheduler-off-v11 mappings remain the current documented planner selection.

The three runtime profiles cover TESS, LIGO, Project8 and TIDMAD through the
existing eleven-unit overlay. New profile identities require fresh workspaces.
The root exp framework pin and lock remain unchanged; they do not install this
standalone pair. Prior receipts remain evidence for their own source versions.

## Original-source evidence

`capture_observation_order.py` extracts the complete `lookup_prior` method and
`_age_seconds` function with `git show` from each original runtime family:
`345c802d`, `7689fd58` and `349b6cd6`. It executes them in separate processes under
UTC, America/Los_Angeles and Asia/Shanghai. Synthetic eligible observations and
explicit helper doubles isolate ordering, median, drift and expiry; the capture
is not a claim to replay original eligibility or calibration-key computation.
The new fixture retains complete extracted functions, source hashes, inputs and
returned arguments. It is not derived from the corrected framework algorithm.

Nine cases at three clocks in each timezone and source family produce 243
complete lookup outcomes. Cases include offset order inversion, drift-window
inversion, equivalent instants, malformed timestamps before/after valid rows,
malformed rows causing historical drift eviction, fractional offsets, naive
local timestamps and normalized leap seconds. Native and historical behavior
intentionally differ for some of these witnesses.

Candidate tests write actual typed observations to a current append-only store,
resolve the selected qualified profile and compare every lookup field with the
original output. Only the synthetic calibration key is replaced with the actual
provider-qualified key. Each expected prior then goes through the production
runtime session and its selected frozen verifier. Feed states, measurements and
predictions match the direct original verifier given the independently captured
prior. This catches a session that forgets to forward historical ordering even
when a direct store call works.

## Executed validation

After creating the candidate infra's own frozen environment, install the three
standalone runtime, planner and preflight packages from this exp checkout into
that interpreter with normal, noneditable installations. From the exp checkout:

```sh
SIDERIUS_CHECKOUT=/path/to/qualified/infra \
  /path/to/qualified/infra/.venv/bin/python -m pytest \
  experiments/shared/runtime_compat/tests \
  experiments/shared/planner_compat/tests/test_runtime_verifier_v8.py \
  experiments/shared/planner_compat/tests/test_scheduler_manual_v11.py -q
```

Result: **202 passed**, exit status 0. This includes existing frozen workload
and session oracles, installed child identity and unknown-assembly refusal,
old timestamp parser witnesses, the new whole-lookup comparisons, existing
historical planner presentation and the current scheduler-off-v11 manual.
Ruff check, Ruff format check and Git whitespace checks passed. Exact source
identities and qualification counts are in [receipt.json](receipt.json).

## Limits

Old local-time interpretation still requires the original host timezone.
Historical sorting intentionally remains lexical, including its malformed-row
and drift precedence. Native default corrections are not disabled globally.
The bare-key preflight path still cannot reuse selected-provider rows; no new
historical preflight reuse mechanism or archived-row import is introduced.

These checks restore the bounded original information flow and decisions; they
do not regenerate deleted files, trained weights, scores or stochastic LLM
responses. No API, GPU, training or dataset access occurred. The old 0.1.5
[qualification](../observation-time/report.md) remains unchanged.
