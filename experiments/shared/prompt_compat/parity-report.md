# Historical rendering qualification

## Contract and exact boundary

This qualification covers explicitly named presentation boundaries in the four
paper tasks and the archived TIDMAD analysis-on failure. It is not a claim that
every historical LLM request or stochastic artifact can be recovered. Infra's
current validators, scoring, execution checks and defaults remain active.
Historical configuration and pure rendering code live in this consumer package.

The exact candidate revision and assembly digest are in
[`qualification.json`](src/siderius_prompt_compat/qualification.json).
The package refuses another assembly until it is independently requalified.
Provider identities additionally pin the implementation, templates, source
inventory, qualification declaration, and override/native boundary map.
The infra comparison base is PR601 (`a3c868554d7863289e36afae70246d839783a0ba`);
the exp comparison base is PR146 (`0c03933cd94c0dea571607716f51926eeca7088e`).
These are separate stacked PRs, not a claim that their prerequisites merged.

## References and profile ownership

| Reference | Exact infra revision | Explicit rendering profile |
| --- | --- | --- |
| TESS | `7689fd58b91d410788e953b51ea69a9dbc528a7d` | `paper-early-v1` |
| LIGO | `0ab1573602c708ddd182432ad4d0e43ae4828c53` | `paper-early-v1` |
| Project8 dual | `349b6cd6d9766abbf3d87515b22e1005599a694b` | `paper-late-v1` |
| TIDMAD NoPrior | `345c802d82c71f72e1b73a90d2bf702d09d1865d` | `paper-tidmad-noprior-v1` |
| TIDMAD analysis-on | `c046744712fabfbd09c5c5a51a84fb30073d59e3` | `paper-analysis-c0467447-v1` |

The early profile omits the later native-training appendix. The late profile
retains it. Implementor, proposer and code validator share that appendix hook.
All profiles freeze the historical proposal templates, including the causal
stage before its later source-identity instructions. NoPrior additionally uses
its historical interpreter rendering functions. Only the analysis-on profile
declares the historical data-analysis boundaries; other profiles refuse them.

[`source-inventory.json`](src/siderius_prompt_compat/source-inventory.json)
records each frozen file's original source hash and packaged hash. The interpreter
module is the selected pure rendering functions plus their source dependencies;
the analysis module is the original pure rendering module. No old node executor
or workflow is copied. These snapshots intentionally retain historical wording
and values; they are experiment provenance, not current framework policy.

## Message and producer comparisons

[`rendering-parity.json`](evidence/rendering-parity.json) records **47 matching
cases** at the candidate revision. Comparisons use each reference checkout's own
frozen environment and the candidate's normally installed consumer package.
Messages are UTF-8 byte compared by SHA-256, without whitespace normalization.

| Cases | Count | Verified claim | Evidence boundary |
| --- | ---: | --- | --- |
| Implementor reasoning | 4 | Full system/user messages from reconstructed first inputs match | Archived proposal, task configuration and declared startup limits; not proof of the missing original request envelope |
| Implementor code | 4 | Full system/user messages match for the supplied reasoning text | Reasoning text is an explicit synthetic witness; original intermediate reply is missing |
| Proposer system templates | 24 | Three stages × explore/exploit × four tasks match | System only; baseline isolation enabled; no reconstructed intermediate user conversation |
| Interpreter | 8 | Archived tuner output through the actual summary producer and renderer matches with structured-health off/on | Explicit empty required-gate set; branch qualification, not every historical interpretation request |
| Code validator | 4 | System text and shared appendix selection match | Explicit absent model-I/O contract; user/review reply sequence not claimed |
| Analysis selection, plan, synthesis | 3 | Typed archived inputs through the relevant renderers match | Plan selection order reconstructed as sorted skill IDs; original selection reply/order unavailable |

Receipts retain fixture hashes and scope per case. Inputs contain declared
archive paths as provenance; these paths are not read by the renderer comparison.
No raw dataset is bundled. The capture tool refuses an unexpected reference
revision, dirty infra source, a borrowed environment, or an unknown boundary.
A failed subprocess or message mismatch makes the comparison command fail.

[`planner-regression.json`](evidence/planner-regression.json) separately records
four successful existing planner startup checks using actual archived model files
and current configuration-manual assembly. The v4 planner package remains a
separate selector; the rendering package neither replaces it nor becomes a default.

## Archived generated-program failure

The reference receipt is from TIDMAD analysis-on, band 4–9, iteration 9, SHA-256
`b60e19459d967a99e5887328c5721d597ab442dc86eb2bdb343d1085bdcb2144`.
The initial reply uses Python `null`; its repaired reply lacks a required seed.
Both raw replies survive and their payload hashes are verified before replay.

The final receipts are `failure-text-reference.json`, `failure-text-native.json`
and `failure-text-profile.json` under [evidence](evidence/). The historical
profile plus `generated_program_retries: 0, plan_retries: 1` reproduces the exact
two request labels, system/user hashes and `failed_after_archived_repair`
termination. Both invalid programs are still rejected. Native behavior retains
the additional regeneration request; replay stops there with
`additional_request_without_archived_reply`, not a fabricated third response.
No generated program, skill, dataset, model, or training process executes in
this archive replay. Earlier `generated-failure-*.json` receipts record the
recovery-only milestone and are superseded for text parity by these final receipts.

## Missing evidence and unclaimed surfaces

- **MISSING_EVIDENCE:** complete proposer intermediate replies/user requests and
  actual implementor reasoning replies. A final merged proposal cannot recover
  those messages. Current proposer vocabulary validation can request corrections
  absent from older source; missing replies prevent qualifying historical branch
  selection. This PR keeps those correctness checks.
- **MISSING_EVIDENCE:** complete validator conversations and all interpreter
  contexts, required-gate combinations and historical brief/overall summaries.
- **NOT_QUALIFIED:** generated-skill promotion and arbitrary data-analysis
  trajectories beyond the declared fixtures and recovered failure. The frozen
  renderer exists, but availability is not an evidence claim.
- **SOURCE_AUDIT_ONLY:** selected reflector functions/constants and literature
  template loading have unchanged source across the audited references. The
  [remaining-surface audit](evidence/remaining-surface-audit.json) records hashes;
  source equality is not proof of complete call inputs. Validator source differs
  for early references because of the training appendix, now covered by its hook.
- Deleted predictions and unavailable stochastic outputs are outside acceptance.
  No new LLM calls are used to invent missing historical replies.

Accordingly, do not describe this as 100% reconstruction of every paper artifact.
It establishes byte equality for the listed recovered/reconstructed information
boundaries and exact control flow for the one archived failure.

## Local validation and maintenance

The infra tests cover default rendering, real-node hook reachability, composition
binding, identity drift, native/override declarations, copied inputs, strict
text output, loader ambiguity, recovery propagation and shared retry limits.
The final relevant local suite passed 167 tests (28 unrelated subprocess cases
deselected); seven separately selected plan-recovery/error cases also passed.
Targeted Ruff and Pyright checks passed.

Targeted schema/resolution, provider, persistence and deadline tests preserve
current rejection behavior. Only relevant local suites and static checks run;
there is no full or remote CI campaign and no API/GPU budget expenditure.

[`installation.json`](evidence/installation.json) verifies all installed package
files against reviewed source, all frozen source inventory hashes, and refusal
of an unqualified assembly for each profile. Use the commands in the README to
regenerate evidence. Future updates must keep archived fixtures immutable or
publish a separately identified case, compare against original source, update
qualification explicitly, and use a new workspace for any changed identity.


## Merge review follow-up

The [merge review receipt](evidence/merge-review.json) records the final review
heads and checks. Review fixed an empty-fixture false positive in the comparison
tool and completed the affected infra node contracts. No production behavior or
frozen rendering implementation changed. The final 47 message pairs and provider
identities remain equal to the original qualification. The expanded, relevant
local set passed 321 tests, plus seven retry/error cases, four planner-package
cases and one empty-fixture regression. Four actual planner startups, 30
producer/history prompt pairs, the historical planner self-check and the archived
failure replay passed. Targeted Ruff and Pyright checks passed. The missing
evidence and unqualified surfaces above remain unchanged.
