# Ordering provenance compatibility (#447)

## Contract and ownership

Infra PR #599 adds `ordering_observation` to newly emitted records and retains
selected ordering on refusals. It distinguishes unresolved current attempts from
missing historical evidence. It does not change ordering selection, data loading,
training, scoring, admission policy or retries. The native planner can see the
new evidence; that diagnostic change is intentional.

The explicit exp provider `legacy-9b78d505cb11-ordering-v2` preserves the pre-#447
history representation for the archived `9b78d505cb11` planner. Its identity hashes
the original provider identity and the adapter source. Original archived modules,
v1 identities and the installation default are unchanged. No automatic version
detection or workspace migration is performed.

`ordering_v2.project_record` consumes raw persisted dictionaries. It validates a
present observation through infra's `OrderingObservation`, projects a deep copy,
and preserves retained field insertion order. Unknown scientific fields are kept.
It is not a general downgrade for arbitrary schema-materialized dictionaries.

| Input producer | Historical planner copy |
| --- | --- |
| Observation absent or null | Preserve all fields |
| Current unresolved outer attempt failure | Remove observation and newly added ordering fields |
| Selected outer attempt failure, including provider failure | Remove observation; retain selected/proposed/override fields |
| Preflight or phase admission refusal | Remove observation and ordering fields absent from the old producer |
| Measured in-training time rejection | Same removal; require the existing `in_subprocess` evidence |
| Selected completed or execution-error record | Remove observation; retain ordering fields |

The adapter checks outer attempt failures before skip statuses: provider outages
can share `skipped_infrastructure_failure` with admission refusals, but their old
field presence differs. Invalid observations, unresolved records without the
qualified producer marker, contradictory refusal phases, and skips without the
required stage evidence raise an error. The adapter never edits saved history.

## Reference and deterministic evidence

`fixtures/ordering_producer_boundary.json` freezes 15 raw records captured through
the unmodified pre-#447 emission boundary at infra tree
`7db002d1a04f076bff1c67b83476052bda569927` (master
`d116d1561124819fa226e4debf89282c87a2e297`). Caller arguments follow the audited
old producer sites. These are controlled producer inputs, not recovered paper
API requests. The new checker never regenerates the oracle.

`python -m siderius_planner_compat.ordering_check` exercises the current emission
boundary and compares projected dictionaries, including serialized key order,
with those frozen records. It then captures the final system/user messages from
`LLMBridge.plan`: 15 individual histories, an old-only history and a mixed history
long enough to enter compaction. All 17 pairs match exactly. Provider clients are
replaced with rejecting clients; no LLM, dataset, training or GPU is used.

The existing self-check still covers 12 current, six early and ten composed-loss
prompt pairs. `paper_check.py --planner-strategy
legacy-9b78d505cb11-ordering-v2` checks the original frozen LIGO-derived branch
oracles without updating their expected digests: 12 pairs with the historical
configuration manual and 12 with the accepted pre-#372 manual. Original v1 stays
the command default.

Use the qualified infra checkout's own frozen environment after normal package
installation. The exp repository's older global infra pin is unchanged and is
not the environment for these paired integration checks. The focused regression
suite is `experiments/shared/planner_compat/tests/test_ordering_v2.py`.

## Paper evidence and limits

Read-only pre/post checks of 109 preserved native workflow outputs across the
11 inventoried TESS, LIGO, Project 8 and TIDMAD units preserve full record dumps,
summaries, ordering manifest views and rendered interpreter messages. The LIGO
production interpreter call also preserves its captured system/user/kwargs.
Controlled task description text was used for that comparison; it is not a claim
to have recovered an original provider request.

The external TIDMAD orchestration archives do call the shared tuner. An additional
read-only scan compares 118 NoPrior and 122 Data Analysis output snapshots through
the same consumers: all load, and pre/post outputs match exactly. Counts include
duplicate snapshots, not independent scientific runs. The Codex and Claude CLI
archives contain no matching `all_records` output in this scan. Their external
agent prompts are not rebound to this planner plugin. Retain their original
launch/source provenance; this check does not certify migration of those agents.

The previously accepted `checkpoint_selection`, `target_standardization` and
`drop_last` configuration-manual differences remain outside #447. See
[paper-parity.md](paper-parity.md). New records intentionally contain more evidence
and are not byte-identical to old artifacts. The supported claim is preserved
old-input consumption and pre-#447 planner prompt parity for the qualified v2
projection. It is not complete replay, recovery of retired predictions, or a
promise of identical new LLM responses, training trajectories or scores.
