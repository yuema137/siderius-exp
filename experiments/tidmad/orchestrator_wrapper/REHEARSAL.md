# Local orchestrator task-package rehearsal

This is a pre-launch integration witness using the actual agent-visible TIDMAD
package. It is not a main experiment, a training/scoring qualification or a
frozen orchestrator information treatment. The common 24-hour task was preserved;
its official clock was never started.

## Exact inputs and environment

| Item | Identity |
| --- | --- |
| Common package source | exp `e1f2218d3341225b8961633e5cd921a4d6a43e8a` |
| Runtime, matching exp pin | infra `7add8006fe6d9d80fa212c273171a62bc501ce03` |
| Generic documentation overlay | infra `195285971b68befd49de21df9726e92deb964cea` |
| Common band | `0-3`, all four files; unchanged main CLI no-advice package |
| Archive SHA-256 | `6bb22bf716cbf313ea23e791013239bacf80308e762d00dde36c46e066609d5d` |
| Agent-public original files | 96, inventoried before overlay |
| Overlay | 27 generic Markdown files plus one additive diagnostic run declaration |

The existing builder ran from a clean detached checkout of current exp main,
with a separate clean checkout of its exact infra pin. Each used its own frozen
environment. The latest wrapper's 14 schema inventories / 407 top-level fields,
seven node examples, 30 Python snippets and links were checked against that
runtime. The overlay's documentation revision is recorded separately from the
runtime revision; no pin was changed to install documentation.

Only the common archive's `input/` tree was extracted into the actor workspace.
Private evaluator implementations/assets, raw training/validation files and
historical experiment results were not supplied. Explicit operator approval
covered sending this task-document view and diagnostic outputs to OpenAI
`gpt-5.6-sol`; a launch rejected before that approval was not executed or counted
as a test. Credentials were injected without exposing their values.

The fresh Codex CLI used the generic skill through workspace discovery. Its
opening prompt asked it to carry out the pre-launch rehearsal described by the
run declaration. That declaration mapped `/work/input` and `/work/agent` to local
paths, preserved original task bytes, and stated actual environment limits:
CPU only, no data/GPU/scorer or composed-task executor, no training/scoring or
external retrieval, at most three native calls including failures, and one
480-second diagnostic clock. Research call order and architecture were not
prescribed. This diagnostic restriction is not the formal orchestrator treatment.

## Observed results

**Outcome: discovery and native invocation observed; task integration not qualified.**
The CLI ran from 18:07:39 UTC on 2026-09-18 for 480.016 seconds and was
terminated by the diagnostic watchdog. No final `readiness.md` or
`readiness.json` was produced. Operator review below is not an actor-authored
completion report.

| Actual native call | Outcome |
| --- | --- |
| Interpretation, cold start | Typed output persisted; correctly reports zero prior experiments. This is not evidence of an interpreter provider round trip. |
| Proposal, default legacy path | One provider reasoning call completed; commit-prompt construction then raised `ProbeConstructionError`. No `ProposalOutput`. |
| Proposal retry, structured pipeline | Raised `DatasetProfileBindingError` before a proposal output. All three allowed native invocations were spent. |

The actor found the generic skill and detailed references, read the common task
and public task configuration, and used native schemas/protocols rather than
writing a replacement scientific implementation. It chose its own initial
interpretation/proposal/implementation plan, then spent the third call on a
proposal retry. No implementer, validator, tuner, training, scoring or submission
was reached. Initial document reading included 21 failed shell reads using an
unset `$1`; the actor recovered with explicit paths. Discovery occurred, but
this trace does not prove complete understanding of every module.

### Request defect: band constraint remained prose-only

Both persisted proposal requests contain `data_scope.file_indices: null`, even
though their prose constrains work to band 0–3. At the pinned runtime,
`DataScope` defines null as the complete dataset, not the current band. With
this task's 20 partitions, that is broader than the four allowed files. No data
execution occurred, so this is an incorrectly scoped request, not observed
cross-band training. These requests must not be reused for a formal run.
Explicit `[0, 1, 2, 3]` scope and verification against the run declaration are
required for this band. Documentation guidance added after this test has not
yet been tested in a fresh actor session.

### Runtime failure: regression request renders a classifier shape

The first proposal request explicitly permits only `regressor` and supplies the
continuous `[B, T]` forward contract. Nevertheless,
`_render_commit_system_prompt` unconditionally evaluates
`render_classifier_output_shape(fc)` while preparing placeholder substitutions
at pinned source line 1457. The guard rejects the nonexistent class axis. The
exception's wording about a candidate declaring `classifier` does **not** prove
that the coding agent selected a classifier; no candidate was produced. This
is a runtime-path defect exposed by the rehearsal, not a reason to change the
task contract. It is reported here without modifying framework code.

### Retry prerequisite: no dataset profile bound

The actor selected a structured reasoning pipeline for its retry. That path
calls `_applicable_dataset_constraints()` and then `resolve_dataset_profile()`;
no dataset profile was bound in this standalone invocation. Supplying a forward
contract and task prose did not establish that binding. The failed retry does
not show whether a fully bound structured pipeline would work. The public-only
composition blocker below also remains; do not infer a qualified alternative
execution route from an importable class.

### Deadline and preservation

The actor's first native subprocess used `timeout 430` after substantial setup,
rather than the remaining shared allocation. It exited before the outer
480-second cutoff in this trace, but this timeout is unsuitable as the sole
budget control. The outer CLI was stopped at the approved limit; a subsequent
host process inspection found no remaining runner or native test process.
Future test supervision should cover descendant process groups and reserve
remaining time for evidence/report writing. No claim is made that the attempted
extra child watchdog produced a receipt.

The runner's final inventory reports no original files changed and no files
added outside `agent/`. The 96 common public input files retain their original
bytes. Native failures and partial results are preserved rather than rewritten
as successful readiness.

## Boundaries and remaining work

An independent offline call to `compose_run_task_bindings` on the unchanged
public `continuous_regression_frozen_pool.yaml` raises `TaskCompositionError`:
the explicitly referenced `../runtime/scoring.py` is intentionally absent.
This is an execution-environment prerequisite, not permission to copy private
scoring files into the actor view or replace the scorer. Some standalone native
operations can accept explicit typed context; this does not supply a complete
composed training/evaluation route.

The next end-to-end test needs a separately authorized environment with the
permitted data, accelerator, native operation bindings and common submission
service. Formal information-treatment choices must be explicit; the CLI
receipt's `not_applicable` module states do not define the orchestrator arm.
Retain the common budget/deadline, full-band evaluation and candidate-artifact
requirements. Current native code/preparation success must not be represented
as trained weights, a score, a Health pass or an accepted submission.

## Evidence

Raw receipts, public-input inventories, actor event trace and native request /
output / failure files are retained in the operator's local
`iclr-orchestrator-wrapper/artifacts/task-integration-20260918/` evidence folder.
They are diagnostic artifacts, not additional task instructions. Representative
SHA-256 identities (paths relative to the rehearsal root):

| Evidence | SHA-256 |
| --- | --- |
| `evidence/receipt.json` | `2d8a6b84eae344e464a81591c09595250a6778fcc5e15a7049a6097176264b6e` |
| `evidence/events.jsonl` | `c4e4330d3c6ef7c11878d437349a9c34a48c3d28354a4a5475dd8b814ead849f` |
| `band-0-3/agent/evidence/native_calls/01_interpretation/output.json` | `e48a19ebbe7a694ee16e1292c11dd42ae1f43da4bd6d112088b77128f98c2017` |
| `band-0-3/agent/evidence/native_calls/02_proposal/input.json` | `aaef535643391c1642a46b4f84fccf01cc9b7a246cbb75a4f094e6232e112026` |
| `band-0-3/agent/evidence/native_calls/02_proposal/failure.json` | `960d63dc535cb1cb05aaf699018d4d3f064de731e01a682251629dd687e26312` |
| `band-0-3/agent/evidence/native_calls/03_proposal_retry/failure.json` | `a0200ed636cd8fa36729c7a7bfee6e1ec1077deadd4198a7ab94f8921cdd2a53` |

No production launch, formal clock, active H100 unit, task semantics, evaluation
policy or generic framework source was changed by this rehearsal.

## Follow-up diagnosis and preparation

The observed failures were reproduced offline on unchanged runtime `7add8006`.
A separate generic runtime repair, [infra PR #536](https://github.com/Galileo-Sandbox/SIDERIUS/pull/536)
(`b07d274c`), fixes continuous-contract commit rendering and has 64 focused
renderer/contrast/regression tests passing. It does not change this repository's
pin or any frozen task file. The repair is not yet merged or live-qualified.

The second failure can be addressed through the existing public
`load_dataset_profile` / `bind_dataset_profile` interfaces using the resolved
profile already in the public package. An offline native pipeline probe reaches
an injected stop at the provider boundary when bound; without binding it raises
the same `DatasetProfileBindingError`. This proves the missing dependency is
available without exposing the private scorer. It does not prove a complete
proposal, full composition, training or evaluation works.

Generic wrapper documentation `abfed67b` now explains immutable whole-package
inputs, standalone profile binding, explicit scope and scope restoration across
handoffs. It contains no TIDMAD band constants. Operator-side offline checks
cover scope 4–9 and non-TIDMAD profiles with 7 and 3 partitions; these are API
checks, not evidence of a new agent independently following the instructions.

A fresh view still matches the original 96-file hash inventory exactly. The new
local test supervisor was checked against a child in another session that
ignores TERM, and normal completion; no child survived. An attempted new real
CLI launch was rejected by automatic approval review before execution, pending
explicit renewed task-document egress approval. No additional real-session
result or improved end-to-end readiness is claimed here.

### Public-only capability assessment

This is a distinction between declared prerequisites and measured completion,
not a claim that every listed API completed in this environment.

| Operation | Available evidence and limits without the private scorer |
| --- | --- |
| Cold-start interpretation | Actually returned a typed result from explicit task context; no scoring needed for that observed call. |
| Proposal | Continuous legacy renderer repaired offline; structured route reaches an injected provider-boundary stop after public profile binding. No successful real proposal yet. Nonempty ranked history can require metric context; the empty cold-start probe is narrower. |
| Implementation | Source exposes a standalone path taking proposal, forward contract, task blocks and writable generated-library paths. A usable proposal is still missing in this rehearsal. Custom-loss/composed branches can require additional task-data bindings. No actual implementation completed. |
| Code validation | Existing API accepts generated artifacts and their Model-I/O contract. Candidate/tests must first exist and be authorized to execute; public files alone do not provide them. No validation of a newly generated real-task candidate completed. |
| Training, evaluation and submission | Unavailable here: public composition cannot load the omitted scorer, and data/GPU/submission service are not provisioned. Standalone reasoning success cannot establish these capabilities. |
| Measured Data Analysis / external retrieval | Not enabled or provisioned in this diagnostic; API presence does not grant permission. |

The supervisor now also covers a successful parent exit with a TERM-resistant
orphan: cleanup shares the original deadline, and a synthetic early readiness
file survives. This is an infrastructure witness, not proof that the next coding
agent will maintain its readiness report. That remains a live-test requirement.

## Authorized fresh retest with the isolated repair

This later test supersedes only the approval-pending status above. The operator
explicitly authorized one additional 480-second session using the same 96 public
files. It used runtime `b07d274ccb8565ee24a1acc0bad01010be3e564c` and generic
documentation `abfed67b0766a1c1afedc27576d2659347fe83f2`; common exp identity
and its recorded dependency were unchanged. The CLI received no previous failure
answers. Source remained fixed throughout this test.

**Outcome: native proposal succeeded; integration still not qualified.**

- The actor read the skill and invocation/provenance guides. Its actual read
  result included the explicit `file_indices=None` warning; this was an
  application failure, not proof the file was undiscoverable.
- An inner approval review initially rejected the provider call. The actor
  preserved and inspected the payload; review then allowed the native call.
  This delay is recorded separately from framework execution.
- The actor used the public profile loader/context correctly. Legacy native
  proposal returned a typed `regressor` result. Both reasoning and commit token
  receipts exist; the former classifier-shape exception did not recur.
- It applied native `local_full_spec` to the proposal. Candidate identity was
  retained in the validated implementer request. Implementation was interrupted
  while waiting on the provider to reserve reporting time; no code/output was
  returned, and no candidate validation took place.
- The proposer request **again retained null DataScope** while its prose named
  band 0–3. No data execution occurred, but this request is unsuitable for the
  restricted formal run.
- The implementer request populated `expert_advice` with the coding agent's own
  instructions, rather than an authorized upstream advice artifact. Although
  these were engineering instructions rather than scientific results, this
  violates the documented source distinction. The original request is retained.
- `readiness.json` was created early, but remained at its initial zero calls /
  empty operations state after actual native attempts. No final `readiness.md`
  was written. An early file alone is not sufficient recovery evidence.

The supervisor sent termination signals at 480.018 seconds. Its final receipt
was written at 481.033 seconds after process reaping, reports no surviving test
processes, and confirms all 96 original files unchanged with no added input
files. No training, scoring, raw data access or formal GPU run occurred.

Raw artifacts and a separate operator audit are retained in local
`artifacts/task-retest-20260918/` after credential-value scanning. Operator
findings do not overwrite or repair the actor's stale readiness file.

Following this evidence, the generic skill now puts a serialized-request check
at the invocation point and links it directly from proposer/implementer guides:
compare actual scope to authorized scope; verify advice sources; persist started
status before invocation and outcome before planning another call. These are
Markdown instructions only, not new schemas or enforcement. They contain no
TIDMAD values or prescribed call order. This latest wording is **not live-tested**.
Further paid/provider sessions require their own applicable authorization; none
is implied by this completed single-session receipt.

Representative evidence SHA-256:

| File | SHA-256 |
| --- | --- |
| `evidence/receipt.json` | `68d896065808efc40f667785c8ea1d42e7d2a1607c41bcd7aea20e322d18f8f1` |
| `evidence/events.jsonl` | `b8bb09ab3795d09c1a2eb8dd250bb5c37ab061d3ba9f5c3c299f8e0a2940d5dc` |
| `operator-audit.json` | `5dfe0c020db9507f84ec1cd29829e2c809b153a25f8f3dcd66efedfe786f862e` |
| `band-0-3/agent/native/proposal/request.json` | `8005d8f1ba4b423541969928e401f5de25c0cff8328cc42af94422316281397e` |
| `band-0-3/agent/native/proposal/output.json` | `08b22712861e8b48c00ec00339e06b441dccde00aec2f5da0e8b2d6fe87cc77c` |
| `band-0-3/agent/native/implementation/request.json` | `2481f031f5b6c769984a8fb3a4da5475ae47f4a9edfe6d8db67849b9eefebc34` |
| `band-0-3/agent/readiness.json` | `ae56ff3b7c4533cfe7813734a1044ebd8a4b7b21e62e67bcca1c26d0b9f912af` |

### CI checkpoint after the retest

The isolated runtime repair at `49330e46` passed automatic CI
[35385727277](https://github.com/Galileo-Sandbox/SIDERIUS/actions/runs/35385727277),
including both unit-test lanes. Its executable source matches the live-tested
`b07d274c`; the intervening change corrects the CLI documentation line citation.
Latest generic instructions `48924696` passed CI
[35385884722](https://github.com/Galileo-Sandbox/SIDERIUS/actions/runs/35385884722).
These results do not qualify the new instructions' agent behavior. The prepared
three-session follow-up batch remains unstarted pending explicit authorization.


## Subsequent authorized three-case batch completed (2026-09-18)

The user explicitly authorized these three sessions. All ran at runtime
49330e46 and documentation 48924696; none remains running. This supersedes the
unstarted/awaiting-authorization checkpoint above. Total elapsed 1030.294 seconds
against the 1200-second allocation. All frozen inventories (96/9/5 files) remain
byte-identical with no added files; all supervisor receipts show zero survivors.
No training, scoring, GPU execution or private evaluator access occurred.

| Case | Elapsed / cap | Observed result |
| --- | --- | --- |
| Public real task | 720.054 / 720 sec | Native proposer, implementer and validator returned typed outputs with the same candidate identity; 3 generated-code tests passed. Scope/report qualification failed. |
| Restored synthetic regression | 159.664 / 240 sec | Passed: native restoration protocol, verified replacement paths, preserved identity/config/Model-I/O, and truthful non-execution report. No candidate or native-provider execution. |
| Synthetic classifier without tests | 150.577 / 240 sec | Missing tests recognized and not fabricated. One native invocation failed with APIConnectionError; no typed validator verdict. Final report correctly says acceptance not demonstrated. |

Real-task request still contained null DataScope: native resolution selects all
20 profile files, while the frozen 0-3 run authorizes indices [0,1,2,3]. Its check
incorrectly claimed this was the selected band. No data execution occurred.
Our additive run declaration omitted explicit resolved indices despite the exp
assembly guidance; this is also an operator preparation defect. Native advice
fields were empty (self-authored advice defect absent), but the check incorrectly
attributed the empty expert_advice to a protocol projection. Do not treat that
provenance check as correct. JSON readiness records all three actual outcomes;
top-level state remained in_progress and requested readiness.md was never written
before the time limit. Successful code validation is not scientific readiness.

Evidence: artifacts/authorized-batch-20260918/, including independently checked
operator-audit.json and all three terminal receipts. Archived only after a known
credential-value scan; raw private evidence stays ignored and untracked.

Targeted documentation changes now require the additive run declaration to cite
resolved native scope and its frozen mapping, and maintain both requested report
formats incrementally. The exp operator example gives the existing frozen band
mapping without changing any task-package file. These new changes are not yet
behaviorally tested. Existing completed fixtures remain unchanged. No fourth
session or extension is authorized by this completed batch. Remaining focused
verification is actual scope comparison and report persistence, not another full
proposal/code-generation run. Goal remains incomplete; PRs remain unmerged.

Representative archived evidence SHA-256:

| File | SHA-256 |
| --- | --- |
| `operator-audit.json` | `4577b6ffa8a9d45705ced1080ca9d6a423474749c65517241ed7e28845aecdaa` |
| `real-task/evidence/receipt.json` | `f7217e5e07dab5f66f599dfba4b0cfef6bc2cbae4790a1ce5586565ed77bcf75` |
| `restored-regression/evidence/receipt.json` | `427f2ed8121a5f3571e5b5842c4c1e84c6298deab6850d504257c743ef16456a` |
| `missing-classifier-tests/evidence/receipt.json` | `53229ce897434771aca119cd8cbaacb8dd969b216e4a1e87fbede561bc882608` |


## Focused scope/report diagnostic: provider interruption

The operator authorized one further 240-second session after the three-case
batch. It ran using runtime 49330e46 and wrapper fd8770e1, with explicit resolved
scope in the additive run declaration. The same 96 frozen files were copied
byte-for-byte. Native provider calls, candidate execution, training and scoring
were disabled; only the outer OpenAI gpt-5.6-sol coding-agent session was enabled.

At 82.632 seconds the CLI exited 1 with `Selected model is at capacity. Please try
a different model.` The actor had read the skill, invocation contracts, task,
profile and source, and recognized [0,1,2,3] in its narrative. It had not created
a typed request, readiness.json or readiness.md. No successful scope comparison
or incremental-report behavior was demonstrated. This is an inconclusive service
interruption, not a successful retest or evidence that prose recognition fixed
the prior request defect. No replacement model, retry session or extension ran.

Independent inventory verification confirms all 96 files unchanged, no additions
and no surviving test processes. Raw evidence, terminal receipt and operator audit
are retained after known-credential scanning in the ignored local artifact folder
`artifacts/focused-scope-20260918/`. Latest generic CI 35389392680 is still in
progress at this checkpoint. PRs remain open; no formal experiment was started.

The remaining behavioral checks are still actual serialized scope resolution and
both reports being maintained. Do not add more guidance based solely on this
capacity interruption. A further external-model session requires new applicable
authorization; this single session has ended.

| Evidence | SHA-256 |
| --- | --- |
| `evidence/receipt.json` | `cea49c34e1299477e2a19c3b22cb6a4204eb89638c05cbce87b602012e933c98` |
| `evidence/events.jsonl` | `047bb0630a5bc9392c14152e32e206a014752bb69cfe182d85361fbd586fa898` |
| `operator-audit.json` | `8ca0920bb20197d540715f5ca26f80f35a5b4e87df262d4735ac2ccd3a828fa4` |


## Authorized retry: scope verified, final reports retained

The operator requested a same-boundary retry after the capacity error. A fresh
session used runtime 49330e46 / wrapper fd8770e1 and the identical 96-file frozen
input, with a 240-second cap. It exited 0 at 220.775 seconds without a capacity
error. No previous actor answer was supplied; previous evidence was preserved.

Independent native `ProposalInput` validation and `DataScope.resolve` against the
20-partition public profile confirm the serialized request selects exactly
[0,1,2,3], matching the frozen provenance band. The null/whole-dataset request
failure did not recur. Advice/evidence fields remain empty rather than invented.
Both readiness.json and readiness.md accurately distinguish a prepared request
from a native result, and identify the absent private scorer/composition binding.
No native provider invocation, candidate execution, training or scoring occurred.
All 96 original inputs remain unchanged, with no additions and no surviving test
processes. Current wrapper fd8770e1 CI 35389392680 is SUCCESS.

Reporting remains a qualified result: the independent observer first saw both
reports at approximately 200.9 seconds, after request preparation; it observed
no earlier checkpoint or subsequent content change. This proves final report
availability before the deadline, not early incremental recovery. The actor also
ran optional framework tests (10 passed after one incorrect path). Its pytest
cache updated in the isolated runtime checkout outside the declared agent-only
write root, although tracked runtime files remain clean. Do not call all write
boundaries satisfied. These findings do not invalidate the checked scope, but
prevent treating the entire diagnostic as unconditional qualification.

Evidence is archived after known-credential scanning under ignored local
`artifacts/focused-scope-retry-20260918/`, including report observations, actual
requests, command log, receipt and separate operator audit. No further external
session was launched. Do not infer universal agent compliance, other-band
behavior, or scientific readiness from this single bounded request preparation.

| Evidence | SHA-256 |
| --- | --- |
| `operator-audit.json` | `1d6dbaa4b11de373e6783c92d9201bd1a845d21f702c1559800bc62f8b8b8f9b` |
| `evidence/receipt.json` | `351a8b3797b56e7e2945f6b3093245e39aa399f39f9476c09f76a0ae1bb56c4c` |
| `agent/proposal-input.json` | `bf393f237051f604b2a26db35014fb4cb10e9d4feb7636860441e8afd44dd5ab` |
| `evidence/report-observations.jsonl` | `5e9fd15e9a4276ceae322c8e4a4fd675e84a344b6d72f0c7d0bea34154ba7286` |
