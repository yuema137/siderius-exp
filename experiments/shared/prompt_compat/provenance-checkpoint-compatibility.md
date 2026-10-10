# Historical plan-resolution provenance presentation

## Ownership and behavior

Infra #678 corrects `ExecutionProvenance.events` to describe the persisted
`TrialConfig`. A separate optional `plan_resolution_events` tuple preserves
the previous plan-only comparison at the producer boundary. The corrected
actual events remain authoritative for ordinary-run reflection feedback. The
provenance object travels from prepared attempt to reflection; it is not an
additional persisted field on `ExperimentRecord`.

Package `siderius-prompt-compat` 0.10.2 registers the generic
`tuner.execution_provenance` boundary in its explicitly selected paper profiles.
Its renderer reads only the preserved plan-resolution checkpoint and renders
the original paper-era block. It does not recompute resolution, inspect task
names, edit events, replace the whole reflector or change execution policy.

The frozen block and authority labels are identical in the four paper reference
revisions (LIGO `0ab15736`, TESS `7689fd58`, Project8 `349b6cd6`, TIDMAD
`345c802d`). `source-inventory.json` binds the original files and packaged module.
The new module is included in the profile's source identity. It calls its own
frozen renderer, never the decorated native renderer, avoiding recursion and
future native wording changes.

| Input | Historical rendering |
| --- | --- |
| `provenance=None` | Empty string |
| `plan_resolution_events=()` | Empty string, even if actual events differ |
| Nonempty checkpoint | Original block using checkpoint events |
| Missing or null checkpoint on a provenance object | Explicit error |

Missing evidence is not an empty historical comparison. The adapter cannot
infer old plan-only events from the corrected execution events. Older framework
APIs never call the new boundary; their existing rendering remains native.
Unqualified assemblies still refuse before profile binding.

## Selection and migration

Install this version into the selected qualified framework's own environment,
using the [existing installation instructions](usage.md#1-install-into-the-infra-environment).
Select the existing matching v2 task prompt profile explicitly. Installing the
package alone changes no native default. The root framework dependency pin and
archived scientific declarations are unchanged.

Use a new workspace for the new package identity. Preserve original packages,
framework revisions and evidence for old workspaces; do not update stored
identities or fabricate checkpoints in archived records. Source qualification
includes the plan/provenance producers as well as rendering code. Qualification
of prompt text alone is insufficient when the producer changes its meaning.

## Offline validation contract

`capture_reflector.py` captures complete system/user requests through the real
`LLMBridge.reflect` method, with provider/network/scoring disabled. It requires
the expected clean framework revision and that checkout's own environment.
It uses archived task/metric inputs and explicitly synthetic provenance cases;
it does not claim to recover historical conversations or actual scores.

For each of the four reference revisions, five cases cover absent provenance,
empty comparisons, corrected-empty/historical-nonempty, the inverse and different
nonempty comparisons. The reference receives its original plan-only events;
the candidate retains both event sets and selects the explicit historical
profile. Complete messages must match, and input provenance must remain unchanged.

For a supplied `CASE`, `REVISION`, `PROFILE`, clean `INFRA_CHECKOUT` and exp
checkout, create a new output directory before running:

```sh
OUTPUT=$(mktemp -d)
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/capture_reflector.py" \
  --case "$CASE" --expected-revision "$REVISION" \
  --profile "$PROFILE" --output "$OUTPUT/candidate"
```

Run the same tool under the corresponding original reference checkout without
`--profile` to capture the reference request. Compare all `*-system.txt` and
`*-user.txt` files byte for byte; receipts bind the task fixture, tool and source.
A capture is rendering evidence only, not an LLM, GPU or training result.

## Executed qualification

The [compact receipt](qualifications/provenance-checkpoint/receipt.json) binds
framework `4d8165a614da410e4e90576fd5c2de026d2203ea` and package 0.10.2.
All four original framework checkouts were rerun in their own environments:
20 complete reflector message pairs matched the candidate byte for byte.
The five witnesses deliberately use synthetic provenance and numeric results;
archived task/metric inputs establish the four task contexts. Raw request text
and private workspace paths remain external to this repository.

The focused suite passed 23 tests, including missing-vs-empty checkpoint
semantics, native/historical disagreement inversion, input immutability, no
recursive native rendering, existing profile qualification and eleven paper-unit
mappings. The previous 47-boundary corpus was rerun on original references and
candidate; all matched. Four SHA-checked archived planner startup model requests
also matched their original complete system/user identities.

Installed source inventory, normal entrypoint discovery and unknown-assembly
refusal passed. The 162-file prompt closure now binds the two provenance
producer files. All 78 estimator-closure files and 18 runtime-verifier files
are unchanged from the preceding qualified source pair; no additional qualifier
or version change was made to those packages. Their installed preflight
source/child/checkout identity check also passed.

No real LLM response, GPU measurement or training was performed. This evidence
qualifies deterministic presentation only; it does not claim that the old
plan-only narrative was correct, or promise identical models, weights or scores.
