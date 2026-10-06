# Historical planner migration contract

This contract originated with infra issue #372. No scientific migration is qualified
by this document alone. Source preservation and offline prompt comparisons are
separate from historical response replay and fresh scientific execution.

## Scope and evidence

Affected scientific experiments with completed run records require individual
source and configuration verification before binding a historical provider.
Failed scientific attempts remain evidence and must not be labeled successful.
Gate, qualification and other internal validation records retain their original
infra revision and evidence; adapting them to new-version default plugins is
outside this migration. A metadata file marked `completed` is not sufficient
to establish a completed scientific experiment.

The initial tracked receipt inventory covers the four paper tutorial demos,
TESS `nop_004`, Majorana's recovered model-demo trajectory and SuperNEMO's
recovered trajectory. It is not a complete census of external workspaces.
SuperNEMO's missing original workspace is an accepted evidence exception: retain
the recovered source and receipt, mark full replay unverified, and rerun later.

The locally inspected V20 workspaces contain failed/error attempts and
`no_records` manifests. They do not establish a completed successful run.
Their source must not be assigned a newer default merely because both sources
contain similar strategy text.

The paper-specific acceptance scope and evidence gaps are tracked in
[paper-compatibility.md](paper-compatibility.md), with verified source mappings
in `paper-source-inventory.json`. Tutorial receipts in the initial inventory
are not substitutes for the paper's formal runs.

## Required migration record

Before calling a scientific migration qualified, retain a separate record with:

- The original receipt identity and SHA-256, original infra revision, and exp
  revision with its verification status. A recovered checkout is not proof of
  the original experiment revision.
- Original prompt source path and digest, the bridge and rendering dependencies,
  and the selected versioned provider. Equal `prompts.py` bytes alone are
  insufficient when the surrounding assembly differs.
- Task, configuration, data and environment identities, plus the supported
  scope of comparison. Record missing evidence explicitly.
- Final rendered system/user prompt comparison against the original code,
  including task appendices, loss inventory, advice and model/config context.
- Whether archived responses were available and replayed; distinguish that
  check from sending fresh requests to a stochastic provider.
- The new workspace and its relationship to the original evidence, the exact
  qualified new infra/package revisions and the explicitly selected provider.
- Any history/model import procedure actually validated. Plugin selection does
  not itself import prior state or establish correct continuation.

Do not store credentials or private data in migration records. Dataset identity
references do not authorize copying or downloading raw data.

## Workspace and default behavior

Keep original workspaces, locks and receipts unchanged. A verified migration
creates a separate workspace and explicitly selects the historical provider.
Never backfill a missing strategy identity in an old lock or copy that lock as
proof that a new run has the same treatment. An unverified source remains on
its original infra revision.

The compatibility installation declares one default for callers that omit a
selector. That default is not a historical-version detector. Each verified
historical experiment binds its own provider explicitly; an explicit selection
overrides the installed default. No default installed, or conflicting installed
defaults, must produce an error. Selecting `native-timing-v1` changes the planner
treatment and must not be represented as historical replay.

## Current validation boundary

For #447, the explicit `legacy-9b78d505cb11-ordering-v2` provider additionally
projects newly persisted ordering evidence to the pre-#447 planner input format.
The old providers and installed default are unchanged. The projection is owned
by exp, runs only on a deep copy supplied to the archived user renderer, and
does not rewrite records, consumer views, or locks. Record the new plugin identity
and qualified infra/package revisions in a new workspace's migration receipt.
See [ordering-parity.md](ordering-parity.md) for the producer mapping and evidence.
The early `legacy-691617f04b42-v1` provider has no new-record v2 qualification.

The operator-approved paper acceptance additionally uses LIGO startup captures
and two sets of twelve shared-branch comparisons. See the authoritative
[scoped report](paper-parity.md) for results, the accepted pre-existing schema
difference and the distinction from full historical replay. Retired prediction
recovery is not a merge condition for this strategy migration.

The package self-check establishes 12 synthetic final prompt comparisons for
the current historical source, six synthetic final prompt comparisons for the
early source with an empty registry, ten current-source composed-loss comparisons,
early call compatibility and
refusal of uncertain registry information. It does not qualify every historical
configuration, non-empty early registries, model/history import, or scientific
replay. The early provider therefore remains restricted as described in README.

Preserving exact prompt bytes does not promise identical newly generated LLM
responses, training trajectories or scores. Claims must identify which of source
preservation, prompt comparison, recorded-response replay and fresh execution
was actually verified.
