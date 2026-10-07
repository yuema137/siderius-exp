# Historical preflight estimator contract

## Owner and boundary

Exp owns `siderius-preflight-compat` 0.1.0 and the explicit
`legacy-078b23ca-preflight-v1` entry point in `siderius.preflight_estimators`.
There is no installed-default entry point. Infra owns typed observations,
provider identity, composition binding, worker dispatch, probing, candidate
order, caps, intensity checks, admission, and failure attribution.

The provider consumes `PhaseObservations` and returns `PhaseEstimate`. It does
not receive a model or dataset and cannot return execution commands. It uses
the unmodified leaf-call parameter sum, leaf output sum/maximum, input/output
bytes, saved-tape bytes, and original training declaration. Corrected registered
state can be unavailable because the historical calculation does not use it.
Native estimation independently requires its own complete observations.

## Frozen arithmetic

The source revision and source hashes are recorded in `provenance.json`.
The package owns the historical 185 MiB context term, 50 MiB backward term,
and optimizer state multipliers (Adam/AdamW: 2; SGD: 0).

- Training admission and diagnostic: saved tape + input + output + leaf-call
  parameters + `(1 + optimizer multiplier) * leaf-call parameters` + context
  + backward workspace.
- Inference admission: leaf-call parameters + leaf output sum + context.
- Inference diagnostic: input + max(final output, maximum leaf output) +
  leaf-call parameters + context.
- Historical optimizer lookup is exactly
  `str(training_config.get("optimizer") or "adam").lower()`.
  It intentionally differs from native validated `optimizer_type` selection.
  An unknown historical identifier raises; no new fallback is invented.

Diagnostic breakdown keys retain their old meanings. Infra still owns rounding,
dominant phase, comparison operators, candidate order and compute-intensity
checks. The package does not undo the truthful refusal attribution introduced
in PR A. New refusal records remain outside planner v6's qualified projection.

## Identity and failure behavior

The profile's sources include implementation, reference provenance and the
qualification manifest. Qualification lists framework assembly hashes, never
the package's own resulting content hash, avoiding circular identity hashes.
No listed assembly means no qualified historical execution. Unknown assemblies
fail before probing. Parent and child must verify the same exact source and
assembly identity. Selection changes composition identity and requires a new
workspace; original archives and locks remain unchanged.

Planner v6 permits version 2 evidence only when its identity matches this
installed source fingerprint and a qualified assembly. The current running
assembly must also be qualified. Native, missing, modified or unknown identities
fail rather than concealing changed numeric input. V6's own identity also binds
this package's projection guard and qualification sources. For archived version 1
inputs, no estimator qualification is required; the existing passing-evidence
validation remains in force. Projection always copies records before removing
additive evidence and never changes estimates, budgets, conclusions or status.

## Offline qualification

`capture_reference.py` must run with the exact frozen reference checkout's own
Python. It rejects the wrong revision or modified tracked source. It captures
45 phase arithmetic cases and 32 completed search cases using actual reference
composers/search with synthetic probe observations. It includes zero and large
byte counts without allocating large tensors, custom candidate lists, cap
equality and adjacent bytes, and intensity-only refusal. It makes no GPU or
training measurement claim.

Tests compare these fixtures to the installed candidate and package, verify
unknown-assembly refusal, configuration immutability, exact identity rejection,
and early/late full planner request equality under explicit unit-test binding.
Test-only assembly binding is not release qualification. Final qualification
must separately list the clean candidate, installed/source equality, actual
archive hash checks, paper source coverage and scoped frozen message results.

No API calls, GPU work, downloads, or training are required for this contract.
Historical prompts and information-flow comparison do not imply deterministic
future responses, weights, scores or predictions.
