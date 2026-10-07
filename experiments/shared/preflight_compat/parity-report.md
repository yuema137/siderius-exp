# Registered-state estimator compatibility qualification

## Qualified candidate and packages

- Infra: `5aa404263c8dfb40662a8ab2f55225d801786984`.
- Estimation assembly: `5fc6e8753d62ac61712c423826e4a6c5af4338aa3be4ba89fb01125001f51656`.
- Rendering assembly: `19f75b7bb07c8a9414071580f33bf16ee68b336b4e17390ad268aa789ea6220d`.
- Combined #419/#615 infra: `334db95a39a988565dcb182c039d866ccd94e55b`.
- Combined estimation assembly: `840146882a60c3eebe0b02d78dac27408a9c7e1e6f60c76cdb6bfecb1a36dce8`;
  rendering assembly is unchanged.
- Installed packages: preflight compatibility 0.1.0, planner compatibility 0.8.0,
  prompt compatibility 0.6.0.
- Published infra pin and original scientific declarations remain unchanged.
- API, GPU and training calls: 0. Bounded CPU forwards are identified below.

## Completed comparisons

All **134 scoped tests passed** in the exp checkout's own environment with
normal, noneditable candidate/package installations. The preceding 133-case
suite also passed in the candidate checkout's own environment; the additional
actual-forward case passed there independently.

[The frozen reference fixture](fixtures/reference.json) was captured with the
clean `078b23ca7d88c2e498be37621e655b1eeb3c8c9e` checkout's own environment.
It records **45 phase arithmetic cases and 32 search decisions** using actual
reference composers/search and synthetic observations. Candidate tests match
diagnostic breakdowns, admission bytes, completed refusals and chosen batches.

An additional **actual CPU forward/search witness** uses the same `Linear(2, 2)`
object four times. With candidates `7, 4, 1` and a cap of the frozen context term
plus 256 bytes, the explicit historical provider reproduces the reference's
batch **4**, while corrected native accounting selects **7**. This confirms
that selecting the installed provider controls fresh search arithmetic while
the infra default retains the fix. It is not a measured GPU peak.

Identity tests reject native or changed providers, unqualified assemblies and
contradictory phase formulas. Early and late historical planner tests compare
complete final requests with the earlier renderer, preserving original records.
The [installation receipt](evidence/installation.json) verifies source equality,
actual entry-point discovery, identical parent/child identities and rejection
of an unknown assembly. The
[prompt installation receipt](evidence/prompt-installation.json) independently
checks frozen source inventory and renderer assembly rejection.

All **47 frozen message cases matched** their historical reference messages.
The [comparison receipt](evidence/prompt-comparison.json) records per-case
scope, source revisions and request hashes. This is the existing bounded
fixture corpus; some cases are reconstructed or system-template comparisons,
not recovered historical conversations.

The [archive audit](evidence/archive-audit.json) verifies **442 source hashes**
and unchanged projection of **331 available records** across all **11 native
paper units**, including every TIDMAD NoPrior and analysis-on band group.
It also records hashes and AST observations for **117 archived model sources**.
That source inspection identifies buffers and direct parameters; it does not
execute those scientific models, reconstruct missing attempts or prove every
historical runtime decision from archived scalar estimates.

## Boundaries and remaining work

Native accounting may change estimates and chosen batches. Historical execution
arithmetic requires explicit task selection and a new workspace. Planner v6
only projects qualified passing evidence; it does not invent old messages for
new static refusals or erase corrected native numbers. Original archives remain
immutable. Equal prompts do not promise equal stochastic responses, weights,
scores or predictions.

## Combined storage and preflight qualification

The clean combined candidate passed **178 tests in one scoped invocation**.
This count includes the shared earlier tests once. Two additional complete
request witnesses exercise the early and late **v7 → v6 → v5** path with both
new evidence streams in the same record:

1. The installed historical estimator selects a batch from actual CPU forwards.
   Its typed v2 decision and diagnostic estimate pass through the production
   worker classifier, adapter and memory-evidence helper.
2. Production storage capture reads a 100-byte temporary fixture's metadata;
   the current assessment records unknown process-counter coverage.
3. V7 projects storage evidence and delegates to guarded v6. Its final planner
   request matches v5 with the corresponding historical input. Raw records are
   unchanged. No LLM or training runs occur.

These are composed producer/renderer witnesses, not a full training workflow or
a claim that an inference probe measured actual GPU capacity. The existing
four-paper storage-shape comparisons also pass on the combined source.

The combined candidate's **47 frozen message cases also match**; see
[combined message comparisons](evidence/combined-prompt-comparison.json).
The [combined estimator installation](evidence/combined-installation.json) and
[combined prompt installation](evidence/combined-prompt-installation.json)
receipts use the final package sources that qualify both framework assemblies.
Fresh configuration instructions select v7 so both historical transformations
are active. Original provider defaults and scientific declarations are unchanged.

This report qualifies the listed standalone and combined candidates. Neither
infra #615 nor public exp #1 can close from B1: activation-lifetime conservatism
and bounded measurement fallback remain separately scoped work. No public
repository synchronization is performed by this qualification.


## Installation across normal merges

The installation verifier records the observed Git revision separately from
qualified reference revisions. It checks that the selected checkout's own
environment loads that checkout and that its complete estimation assembly
matches the invoking environment and a qualified assembly. A normal merge that
changes Git ancestry while preserving those sources is accepted without editing
the provider qualification or identity. Dirty source, different installations,
unknown assemblies and child-identity mismatches remain refusals.

Three additional checker tests passed in the combined infra checkout's own
environment: changed revision with unchanged provider identity, mismatched
assembly, and wrong source installation. Under exp's normal wheel installation
these three checkout-specific tests explicitly skip; that skip is not their
acceptance evidence. Both recorded installation receipts were regenerated with
the final verifier. The provider and renderer sources were unchanged, so the
178-case and 47-request qualification above remains applicable.
