# Static preflight evidence qualification

## Candidate and explicit packages

- Infra candidate: `078b23ca7d88c2e498be37621e655b1eeb3c8c9e` (Galileo-Sandbox/SIDERIUS#616).
- Rendering assembly: `849a69c8363a0538bff7314c27bc820714412a6345c2df5f3b20c5061426ee2e`.
- Normal installed packages: planner compatibility 0.6.0; prompt compatibility 0.5.0.
- Published infra pin, original paper declarations, and prior provider defaults remain unchanged.
- API calls: 0. GPU calls: 0. Training calls: 0.

## Verified boundaries

The clean candidate and each historical reference used their own checkout's
frozen environment. All **47 frozen request cases matched** their reference
messages, including TIDMAD analysis branches. The
[comparison receipt](evidence/static-preflight-comparison.json) records per-case
revisions, identities and message digests. This is the existing scoped fixture
corpus; it is not a claim that every historical conversation was recovered.
The [installation receipt](evidence/static-preflight-installation.json) checks
installed/source equality and refusal of unknown rendering assemblies.

All **44 planner compatibility tests passed** against the installed packages
and clean candidate. The new v6 provider composes the existing historical v5
renderer and removes exactly two validated passing-preflight fields from a
copy of its input. Tests compare complete early/late planner requests with
v5, preserve input records, cover later training/time refusal, and refuse
unqualified new static refusals or malformed evidence. See the
[planner contract and archive inventory](../planner_compat/static-preflight-compatibility.md).

The archive audit covers all **11 native workflow units** in the authoritative
paper mapping: TESS, LIGO, Project8 dual representation, four TIDMAD NoPrior
band groups, and four TIDMAD analysis-on groups. It verifies **442 source file
hashes**, **331 unique records**, and **333 available worker results**. Available
workers completed; no physical or static refusal was found. V6 projection of
all 331 archived records preserves object equality and does not mutate inputs.
External orchestration/CLI baselines and unarchived attempts are outside this
native workflow qualification.

Infra's added composed regression runs the actual inference resolver and wrapper
with bounded synthetic probe observations, then the production classifier in a
real subprocess, JSON loader, adapter, tuner record, planner/proposer renderers,
and repeated-failure summary. It preserves the actual custom batch 3 and decision
8,589,935,646 bytes against 5,368,709,120 bytes. No GPU measurement is fabricated.
Separate accepted-producer tests preserve existing diagnostic numbers while
retaining the new typed evidence. Both initial failure and post-success failure
summaries avoid unsupported model-shrinking or architectural-ban claims.

A separate [decision parity receipt](evidence/static-preflight-decision-parity.json)
compares **1,872 completed inference decisions** against pre-change infra
`05698b0dc4f252af825875f6a006c68b80b1ee13`: **zero differences**, 1,156 accepted and
716 refused. It includes 288 actual CPU probe cases and 1,584 frozen large-byte
cases without huge allocations. Repeated/distinct modules, cap equality ±1 byte,
linear/quadratic scaling, intensity boundaries, candidate lists and semantic batch
ceilings are covered. This establishes bounded decision parity, not GPU peak
accuracy, allocation-exception parity, timing behavior or training replay.

## Intentional changes and remaining work

Infra now stores the exact static decision and distinguishes it from measured
GPU capacity. Default planner/proposer messages change accordingly. Unknown or
contradictory worker outcomes fail closed. Static refusals still skip training;
completed admission formulas and chosen batches are unchanged. Successful legacy
diagnostic values remain unchanged. Raw saved evidence is never rewritten.

For a new historical-mode workspace that emits passing static evidence, explicitly
select the corresponding v6 planner provider. A new static refusal fails that
projection rather than recreating a misleading old claim. Old workspaces retain
their original revision/package identities; this does not authorize in-place
continuation. Installing or upgrading these packages does not select v6 or change the existing
declared installation default.

Conservative inference false rejection and shared-parameter accounting remain
in infra #615 for separately designed PR B. Therefore infra #615 and public exp
#1 remain open after these companion changes. Exact prompt/input equality is
not a guarantee of identical stochastic LLM replies, trained weights, scores, or
predictions. This qualification does not modify the release pin or synchronize
the public repository.
