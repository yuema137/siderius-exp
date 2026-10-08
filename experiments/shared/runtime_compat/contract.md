# Historical runtime verifier contract

## Ownership and activation

This directory owns the normally installed `siderius-runtime-compat` package,
three `siderius.runtime_verifiers` entrypoints, a versioned paper launch overlay,
and original-source timing oracles. Infra owns provider discovery, typed policy,
identity validation, admission, child transport, observation storage and default
behavior. No task name, historical numerical rule or paper selector is added to
infra. Installation alone changes no behavior.

`paper-measured-completion-v1.json` supplies common launch parameters plus a
unit-specific `--runtime_verifier`. All eleven native scientific units from
`../planner_compat/paper-replay-369.json` are covered, preserving their recorded
launch hashes and infra revisions. Apply the overlay only to a copied launch in
a fresh external workspace. Archived files and previous qualification receipts
remain immutable. SuperNEMO and non-native orchestration are outside this scope.

`runtime_completion_policy=verified-prediction-v1` requires verified predictions;
`completed-workload-v1` is the corrected infra default. Historical factories
reject the latter rather than silently combining old timing algorithms with new
finite-workload admission. Trial and Formal time admission are both explicitly
`measured`. Other resource, budget and task validity checks remain applicable.

## Frozen implementations and adaptation

`source-inventory.json` owns source revisions and original/packaged file hashes.
The only change to frozen `adaptive_*.py` files is relocation of the import of
`SteadyStateConfig` and `SteadyStateDetector` to the packaged `steady_state.py`.
That helper is byte-identical across all five recorded historical revisions.

| Profile | Original behavior | Paper units |
|---|---|---|
| `legacy-345c802d-verifier-v1` | No later fast-suffix branch; wall clock from first observation | Four TIDMAD NoPrior units |
| `legacy-7689fd58-verifier-v1` | Original fast-suffix capacity rule; wall clock from first observation | TESS, LIGO and four TIDMAD analysis-on units |
| `legacy-349b6cd6-verifier-v1` | Original fast-suffix rule plus explicit active intervals | Project8 dual representation |

The adapter delegates state, timing, feed, finalization, measurement and
prediction to the selected frozen implementation. `active_interval()` is a
no-op for the two versions that originally did not exclude inactive gaps;
Project8 delegates to its original owner. `permits_workload_completion` is
false. No adapter reconstructs stable observations or substitutes timing values.

Configuration is validated by the frozen schema. Unknown fields are rejected.
For the oldest profile only, the later native transport field
`fast_phase_min_observations` is removed if its value is exactly the current
transport default, 100; a different value is rejected. This cannot activate a
fast-suffix branch absent from that algorithm. The API cannot distinguish an
explicit 100 from the transported default. Assembly qualification binds the
current configuration schema and prevents assuming that future defaults match.

## Identity and environment boundaries

Each profile declares the package factory, adapter, all imported frozen modules,
source inventory and qualification file as source identity inputs. Its identity
also binds the infra runtime verifier assembly. `qualification.json` is an
allowlist of qualified assemblies. Its current candidate is infra `ec92186d`
(assembly `0be63770919ae1636a7a2ad316b2b4da3bce9e1885e3e46759359231999a3bad`).
The [qualification report](qualification-report.json) records the installed source
hashes and passing offline checks; independent review and final pairing remain
pending. Unknown assemblies fail closed. Profiles have explicit version `1`; no implicit
historical default or automatic fallback is installed.

The launch and execution environments must install the same package and paired
infra. Infra resolves selection into `runtime_verifier_identity`, serializes it
with `RuntimeControlPolicy`, and checks it again before creating a verifier and
consuming phase evidence. Installing into only one environment is insufficient.
Follow the single installation procedure in README.md; do not mix source roots
through `PYTHONPATH` or editable installs from another checkout.

New observations retain truthful provider identity. Infra separates calibration
keys by provider identity, so old unlabelled observations are not silently
reused or relabelled as this profile's evidence. Original policy identity bytes
are not a replay requirement: any necessary historical prompt presentation is
an explicit exp projection, never mutation of the raw record.

## Explicit historical presentation

`siderius-planner-compat` 0.9 provides two new explicit profiles,
`legacy-9b78d505cb11-paper-verifier-v8` and its `paper-late-verifier-v8` counterpart.
They wrap the existing storage v7 provider; older profiles and the installation
default remain unchanged. The eleven-unit overlay declares the corresponding
external `tune.planner_strategy` alongside the launch arguments. This is an LLM
configuration setting, not a standard-workflow CLI flag.

The runtime package owns `historical_identities()` and
`require_historical_identity()`. The planner v8 source identity binds those exact
qualified profile identities plus its own source and inherited v7 identity.
Only selecting v8 requires the optional `historical-runtime` package dependency;
importing or selecting an older planner profile remains possible without it.

For a new runtime policy, v8 requires all three provenance fields, exact matching
package-owned and registered verifier identity, `verified-prediction-v1` and
measured admission. Unknown policy fields, incompatible selection and any phase
completion evidence refuse. It removes only `runtime_completion_policy`,
`runtime_verifier` and `runtime_verifier_identity` from a deep-copied prompt
representation. Measurement, prediction, numeric admission, status and the
original saved record are unchanged. Archived records without those fields
retain their existing representation. This does not establish completeness of
an arbitrary full workflow's earlier or later information flow.

## Evidence and limits

Read-only inspection confirmed that all 130 preserved root/iteration lock files
select measured Trial and Formal admission. The five exact historical chain and
CLI revisions corroborate these defaults. Among 331 aggregate attempt records,
22 TESS records and one Project8 record observed their entire same-unit declared
training workload but failed steady-state verification. No equivalent matching
LIGO/TIDMAD record under this bounded predicate does not prove they are
unaffected; all eleven units therefore select an explicit historical profile.

`fixtures/paper-finite-workloads.json` preserves those 23 traces, original record
hashes, workspace-relative provenance, workload, verifier configuration, prior,
observed rates and elapsed time, and archived measurement/admission/status.
The original TESS and Project8 source interpreters reproduced all 23 complete
measurement dictionaries. The fixture proves timing-boundary integrity, not
later validation, checkpoint success or whole-workflow execution.

`fixtures/branches-*.json` were produced by the exact original source checkouts
using `capture_reference.py`, with input and driver hashes. They cover stable
verification, fast-suffix availability, pathological units and inactive-clock
gaps. The candidate must match those outputs without rewriting the oracles.
The two original fast-suffix failures that newer native infra would accept are
particularly important: matching only pre-fix infra would miss this gap.

The installed candidate passes 65 focused tests: all 23 session outcomes match
the unchanged original measurements, predictions, statuses and admissions; all
12 original version-branch oracles match; all 11 paper-unit flag sets pass the
actual standard CLI and launch projection; three independent children resolve
the same identity and construct the selected historical verifier. Controls reject
missing providers, changed identities, unknown assemblies and incompatible
completion selections. The report verifies 17 installed infra closure files and
all eight package identity files against the source checkouts. Both installs are
normal, noneditable installations in this exp checkout's own environment.

The subsequent [presentation qualification](presentation-qualification.json)
preserves the initial report as evidence of its earlier source checkpoint.
Original TESS and Project8 interpreters recaptured all 23 sessions independently;
`fixtures/paper-session-policies.json` preserves their policy values, complete
component hashes and capture provenance. Actual current sessions match those
original components and admissions. Wrapped in a minimal planner record, their
v8 requests match the original-policy v7 requests byte-for-byte; the same new
inputs intentionally differ under v7. This is a session-to-request boundary
comparison, not a complete execution-produced experiment record.

The 47 separate original-reference request comparisons also match (94 system
and user message bodies). Focused projection, refusal, existing storage/runtime
presentation and verifier checks total 132 passing tests. Independent review and
final release pairing remain pending; no future combined source is qualified by
these checks against `ec92186d`.

Infra owns generic native completion and boundary tests;
exp owns historical selection and comparisons. Prompt equality is not proof of
live control-flow parity. No complete conversation, training, score reproduction,
API call, GPU execution or dataset download is claimed by these offline checks.
