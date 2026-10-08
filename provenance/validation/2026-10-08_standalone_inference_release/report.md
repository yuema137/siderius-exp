# Standalone inference release qualification

The consumer pin advances from `46ee9920` to
`b13b9263c939c33b8d06361b1ae2fd0f99c3a900`. This revision repairs missing
setup evidence in fresh standalone generic inference and shares the executor's
watchdog/plain launch selection. It retains the previous accounting interval
for resumed generic inference. Scientific configurations, archived results and
all earlier qualification rows remain unchanged.

## Scope and accounting boundary

Fresh standalone inference starts its setup clock before model construction,
records measured setup, and passes through normal completed-workload admission.
A controlled 20-second setup plus 7-second inference rejects a 25-second budget
and admits a 40-second budget. Real child tests also advance the clock during
model construction to detect a clock that starts too late.

Resumed inference preserves its earlier setup component. The complete
`InferenceRuntimeEvidence` class AST and `generic_inference.py` bytes match
`46ee9920`. Controlled clocks verify both completion policies: a 20-second
model preparation interval remains excluded, while one second of dataset setup
and four seconds of iteration produce a 5-second prediction and actual.
This existing exclusion is a known limitation. General preparation-cost
accounting and its historical-policy pairing are deferred to
[infra issue #673](https://github.com/Galileo-Sandbox/SIDERIUS/issues/673).
The broader `d93ab515` candidate was superseded before consumer qualification.

## Source review

[source-review.json](source-review.json) captures source bytes from each current
canonical digest owner, including newly declared
`core/runtime_control/phase_launch.py`; it does not reuse an old member list.
Runtime has 18 members and preflight has 78. Rendering's 158 members and the
planner's 10 members have unchanged bytes.

The launch helper preserves watchdog keyword presence and the ordinary runner's
result projection. Admission and cleanup remain owned by the executor. Existing
binding and batch resolution are reused within each phase. The source changes
were independently reviewed in infra's structural and standalone-only slices.
Historical verifier algorithms and static estimation arithmetic are unchanged.
Only runtime and preflight receive new qualification rows; rendering needs none.

The prior typed-composition source receipt calculated the planner fingerprint
with `src/`-relative keys, while its canonical owner uses keys relative to
`src/agent/`. Its planner digest was an evidence-generation error. This receipt
uses the canonical owner's digest
`d1321a044c946859faa180a21c4eda21ca8fe79ff838a0c816bc68e5ba265b3b`.
Planner source bytes and historical planner behavior did not change. Earlier
receipts are retained as historical records.

## Executed checks

[receipt.json](receipt.json) records the exact revisions, commands, case hashes,
source identities and limitations:

- 47 archived/reconstructed requests and all 94 message bodies match their
  declared original-source references. Each case retains its own scope.
- 44 routes from four configurations in this consumer checkout equal the
  previous routing receipt, including configuration source hashes.
- 36 focused planner, paper-overlay and tutorial-setup tests pass.
- 143 additional historical verifier, child identity/refusal, finite-trace
  decision and static-estimation tests pass.
- Normal, noneditable installations of all four compatibility packages match
  their 51 source files in both checkout-owned environments; independent child
  identities agree with their parents and with the other environment.
- Installed framework bytes match every canonical source member. Prompt source
  inventory checks and unknown-assembly refusal pass; preflight source,
  qualification, child identity and unknown-assembly checks pass.
- Infra's 16 targeted lifecycle/admission tests pass; independent review ran
  13 preparation and real-child cases. No API, GPU or training campaign ran.

The consumer environment was synchronized from its exact updated lock with
`uv sync --group dev --frozen`, then received normal installations of the
selected compatibility packages. The dependency retains its declared public
URL, but fetching used a command-scoped rewrite to the development repository.
No persistent Git configuration or public synchronization occurred. Public-host
availability remains a separate release check.

## Limits and identity effects

The new runtime/preflight qualification data changes those installed package
content identities. Use a new external workspace with this source pair; retain
old environments and records for historical identity locks. Frozen adapters,
scientific inputs and existing qualification rows are preserved.

Archived message equality does not prove complete conversation, stochastic
training, score or model-output reproduction. Static qualification excludes
protected/measured GPU execution and does not repair incomplete historical
producer geometry evidence. The retained resumed-preparation omission is not
a claim that all runtime costs are accounted for.
