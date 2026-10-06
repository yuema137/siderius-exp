# Explicit historical attempt-role projection

## Ownership and contract

Infra issue #369 corrects role recording and locks validation limits. Ordinary
new runs retain the correction. Exp provider
`legacy-9b78d505cb11-attempt-role-v3` is an explicitly selected historical planner
input projection, built on ordering-v2. It does not patch infra defaults, change
scientific execution, rewrite stored records or alter v1/v2 identities.

The boundary accepts raw recorder history. `attempt_role` absence/None means
historical input and does not trigger role conversion. A present marker must
pass `ExperimentRecord` validation. For the producer vocabulary audited at
infra `120078577261e60d3d3cab672bce6c11df54dcd0`, completed trial records keep
`is_trial`; completed formal records and failure/skip records omit it, as those
raw producers did before the correction. The marker is removed only in the copy
passed to the historical renderer. Unknown producer statuses and unqualified
unresolved roles refuse. The subsequent ordering-v2 projection retains its own
qualification rules. Normalized model dumps are not a qualified replacement for
raw recorder input: filling defaults can change historical prompt representation.

The provider identity hashes its source and the unchanged v2 identity. Select it
explicitly and record the resulting identity in a fresh workspace; no existing
installation default is replaced. Corrected ordinary histories may cause
intentionally different later planner decisions. Exact historical planner text
is an opt-in experiment capability, not the default behavior of infra.

## Reproduction conditions and observed defect

`paper-replay-369.json` preserves launch conditions for the 11 native workflow
units in the existing paper source inventory. Each launch omits both validation
limit flags; the five referenced historical infra revisions declare defaults
`None` and transport them from the CLI. The inspected shell resets these flags
before argument processing. Records with a workload-ceiling receipt confirm the
proportion ceiling was disabled. A launch receipt does not certify absence of
unrecorded later external overrides. No other paper comparison system is newly
qualified by this inventory.

The record audit joins `run_output*.json` / `all_records` to each saved
`trial_config_<exp_id>.json`. TESS has 28 `skipped_time_risk` entries labeled
formal whose corresponding configuration is trial; Project8 has one. TESS's
other two inspected time skips actually are formal. LIGO's inspected outputs
contain no non-success entries; the eight TIDMAD workflow units' non-success
roles agree with their saved configurations. Do not retroactively rewrite these
archives. Trainer `experiment_results_*.json` files contain training metrics,
not the role records under investigation.

`validation_max_samples` bounds training-time validation rows. It is not an
alias for final formal metric evaluation size. Locking either validation limit
does not change its execution semantics. Original datasets, splits, agent
settings and model code remain owned by the referenced experiment assets. The
analysis-on TIDMAD launch also used generated external compositions; their
historical paths and composition fingerprints are recorded separately, and
this change does not claim to reconstruct or bundle those inputs.

## Verification and limits

`python -m siderius_planner_compat.attempt_role_check` drives the current infra
emission boundary for 15 frozen producer cases with both trial/formal roles,
compares the projection to the pre-447 raw-record reference, then compares 30
complete system/user messages through the production `LLMBridge.plan` assembly.
The bridge captures messages and forbids provider client access. The test also
checks that the saved current record is not mutated. Pre-plan unresolved cases
are retained in this matrix. Existing ordering-v2 checks continue independently.

This establishes the changed role/ordering boundary for controlled inputs; it
is not a recovered archive of every scientific LLM request, a full workflow
replay, or a guarantee of identical fresh stochastic responses and scores.
Source/configuration preservation, prompt byte parity and complete artifact
reproduction are separate claims. No paid API call, dataset download or GPU
training is needed for this deterministic comparison.

Additional read-only raw-summary audit: 30 actual skipped-trial records (29 TESS,
one Project8) round-trip through a reconstructed corrected role and the explicit
projection without changing raw JSON or the rendered historical user text under
a fixed context. Twenty-nine also occur in the inspected run-output snapshots;
one TESS entry survives only in the summary population used by this check. These
are original records, not recovered complete original requests.
