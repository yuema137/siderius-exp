# siderius-exp Contributor Rules

This file owns repository contribution policy. Scientific and execution
contracts remain with their task, experiment and framework owners. Source,
validated declarations and relevant tests establish implemented behavior.

## Repository and scientific ownership

Framework defaults follow the current generic contracts. A fix need not
preserve an erroneous old default. Historical scientific behavior belongs in
explicit, versioned experiment-owned configuration or compatibility profiles,
using generic framework interfaces where needed. Do not restore it as an
implicit framework default or rewrite archived evidence.

Before reporting where work lives, verify the current checkout with
`git rev-parse --show-toplevel`, `git rev-parse --git-common-dir`,
`git branch --show-current` and `git remote get-url origin`. A temporary
linked worktree belongs to the repository identified by its Git metadata.

- `tasks/` owns scientific meaning, data identity, splits, plugins, model I/O,
  objectives, metrics and validity rules.
- Workflows own execution and Trial/Formal progression. `experiments/` binds
  a task and workflow to concrete parameters, advice, budgets and result identity.
- `campaigns/` owns authorization and coordination across units.
  `deployments/` owns machine and scheduler setup.
- Generic framework mechanisms belong in SIDERIUS. Consume its native schemas,
  composition, training, scoring, Health and provenance contracts; do not copy
  their policy into an experiment launcher or infer task behavior in infra.
- Raw datasets, workspaces, generated models, caches and credentials stay
  external to both source trees.

Preserve frozen scientific identities. Changes to scientific meaning require
a new task identity; workflow treatments require distinct experiment identity.
Recorded outcomes and receipts do not authorize a new launch. Verify scientific
claims against the selected task, data, source pins and execution evidence.

## Pull request scope and structured-coding workflow

These are binding project principles for implementation, documentation and
release preparation:

1. **One PR, one clearly defined problem.** A PR may cover a small set of issues
   only when they are tightly related and belong to the same reviewable change.
2. **Separate unrelated work.** Keep unrelated bug fixes, new features and
   documentation work in separate PRs. Documentation needed to explain the
   behavior changed by a PR belongs with that change. Record incidental findings
   as scoped issues instead of silently expanding the active PR.
3. **Merge dependencies incrementally.** Develop, independently review, validate
   and merge dependent changes in a deliberate sequence. Do not accumulate them
   into a giant release PR. Component reviews do not substitute for a reviewable
   final diff. Release preparation assembles already merged, validated revisions,
   tags and release notes.
4. **Declare scope before editing.** State the problem, affected boundaries,
   included issues, non-goals and required validation. If the scope materially
   grows, stop expanding the current PR, explain the change and split the work
   into separately reviewable steps before continuing.

Apply these principles at each structured-coding checkpoint:

- **Audit and plan:** read the affected code, define the bounded outcome and
  record the PR boundary and dependency order in the local plan.
- **Implement:** keep changes within that boundary; log adjacent findings as
  separate issues and keep necessary behavior documentation synchronized.
- **Ready for review:** compare the actual diff against the declared scope.
  Split unrelated changes before requesting independent review. Include the
  relevant validation and production/paper-compatibility impact.
- **Merge and close out:** fix review findings, complete the relevant checks,
  merge the bounded PR and update or close only the issues it actually resolves.
  Then proceed to the next dependent PR.

This section is the authority for PR scope; local structured-coding plans and
agent entrypoints must refer to it rather than maintain competing rules.

## Local planning and handoff

Keep plans, step/PR designs and handoffs under
`.structured-coding/plans/<effort>/`, with one authoritative plan per effort.
Keep `.structured-coding/` ignored and untracked; never commit, push or
force-add it. Public documentation belongs in the tracked documentation tree.
Local workflow entrypoints refer to the PR-scope section above.

Record scope, dependencies, decisions, acceptance criteria, validation,
unresolved findings and the next bounded action. Before resuming after a
handoff or compaction, reread the applicable plan and verify the checkout and
changed paths. Obtain missing required scope or approval from the operator;
do not infer it from a status document.

Markdown owns any corresponding HTML rendering. Reading mirrors follow the
authoritative document and must not introduce requirements or approval.

## Environment and launch credentials

Run `uv sync --group dev --frozen` in the exact checkout and use its own
`.venv/bin/python`. Use the exact framework revision in
[SIDERIUS_REVISION](SIDERIUS_REVISION), consistent with
[pyproject.toml](pyproject.toml) and `uv.lock`. A reproduction launcher with
its own explicit pin retains that binding. Do not borrow another checkout's
virtualenv, editable install or `site-packages`, or mix source revisions
through `PYTHONPATH`. System Python is unsupported.

Tests that inspect or execute framework source require an explicit
`SIDERIUS_CHECKOUT`; bind it to the expected revision and follow the selected
experiment's checks. Framework Python commands use that checkout's own
frozen environment. Container execution must preserve the selected lockfile
and source/package revisions; external mounts supply data, workspaces and
machine-owned secrets.

Before each API-backed launch, inject the enabled providers' required keys from
a trusted mode-600 external credential file or managed secret into the launching
process. Perform a name-only presence check before effects. Never print, log,
shell-trace, commit or upload values. Key presence is not proof of provider
access. A checkout dotenv loader does not replace an explicit launch-process
binding. Preserve explicitly reviewed bindings; clear only inherited conflicting
overlays. Follow the selected launcher's checks and the
[credential contract](experiments/shared/workflow_credentials.md).

## Coding standards and portability

- Read the affected task, experiment, schemas and tests before editing.
  Resolve material uncertainty about scientific semantics or public contracts
  rather than inventing a fallback.
- Validate external configuration and LLM-generated execution inputs with
  Pydantic before use. Execution reads the validated object. Reuse the pinned
  framework's native types and APIs rather than creating equivalent competing
  contracts in launchers or task adapters.
- Keep functions focused, inputs/results typed and effects explicit. Use small
  composable boundaries for scientific policy, execution, persistence and
  presentation. Do not enlarge a giant orchestrator or add speculative
  inheritance, dispatch or task branches.
- When extracting responsibilities, prove production reachability and behavioral
  parity. Preserve public APIs, CLI/configuration and serialization contracts,
  source identity, scientific arithmetic, ordering, retry/round and
  timeout/signal semantics. Keep semantic changes separately reviewable.
- Size and complexity are review signals. Check responsibility boundaries when
  functions exceed roughly 100–200 lines or modules exceed 1,000–2,000 lines.
  Decompose unrelated concerns, not arbitrary line counts. Keep refactoring
  necessary to the current bounded change.
- Use the configured checks in [pyproject.toml](pyproject.toml); do not claim
  stricter or broader validation than the tools actually ran.
- Derive repository paths from the executing file or established helper. Obtain
  machine/data/workspace/cache/executable paths from explicit configuration,
  environment variables or fixtures. Do not hardcode a developer's clone,
  username or home directory. Label machine-specific deployment examples.
- Tests must use their own checkout and temporary directories. Declare and
  validate external resource requirements; skip or fail informatively under
  the test contract rather than falling back to another clone or dataset.
  Scripts resolve from their own location or a supplied root.
- For meaningful path risk, verify the affected behavior from an unrelated
  checkout path, including paths with spaces where relevant. Fix the smallest
  confirmed scope, preserve a discriminating regression and track adjacent
  findings separately.

## Validation and independent review

Choose checks from the changed authority and its failure modes. Every added
test must name a real defect and the assertion that fails when it breaks.
Do not retest schema declarations or compare an observed value with an
expectation derived from the same implementation. Preserve distinct input
classes, regression witnesses, production reachability and safety-prompt
coverage when consolidating tests.

Run focused tests and relevant static checks during implementation. Do not run
a local full suite, split it into chunks or dispatch duplicate CI without an
explicit need. Use automatic PR checks where configured; otherwise declare the
required focused commands in the PR. No CI claim follows merely from opening
a PR. API, GPU and external-data qualification are separate from deterministic
tests and must match the authorized launch scope and selected experiment.

Record exact exp/framework revisions, commands, actual tool status and test
summaries. Read the log; a successful wrapper or pipeline is not a test verdict.
Use `pipefail` or capture the test process exit status. Final release/full-suite
evidence uses clean committed source. Do not weaken pin, identity, scope or
resource checks to make a qualification pass.

Obtain independent review of the final bounded diff, fix findings and rerun
affected checks. State scientific, production, paper and compatibility impact;
distinguish source inspection, offline command preview and executed runs.
Report limitations explicitly. Before merge, synchronize affected task/plugin,
experiment, launcher and tutorial contracts with the final source.

## Paper tutorial ownership

For notebook/task/experiment/launch responsibilities, follow the owning
[tutorial support contract](tutorials/paper/implementation.md#tutorial-responsibility-boundary).
Keep training/execution owned by saved scripts. A Run All quick-demo cell may
explicitly invoke its saved script; notebook cells must not reimplement
training or construct provider calls. Disclose API/GPU effects before the
cell, and reuse completed unchanged runs without silently relaunching them.

Tutorial users edit only their initialized external project: copied notebooks,
tasks, experiment JSON, LLM routing and generated scripts. Never prescribe
changes to tracked repository templates as a tutorial step. Distinguish the
project root from each fresh run's output workspace. Advice activation must be
explicitly supported by the selected treatment; an example file is not active.

## Documentation audience and review

This rule applies at every directory depth, including source, tests, examples,
deployments and archived documentation. Classify Markdown by filename,
case-insensitively:

- Only files named `README.md` (case-insensitively) are
  **human-facing**. Assume a technically literate reader who is new to this
  project. Lead with purpose and prerequisites, then give ordered steps,
  concrete commands, expected outputs and effects, and where to change inputs.
  Explain project-specific terms when they first matter; preserve exact CLI
  flags, filenames, schema fields and established technical terminology.
- All other Markdown files are **agent-facing technical references**. State
  scope, owners, interfaces, schemas, invariants, defaults, failure behavior,
  side effects, validation evidence and unresolved limitations as applicable.
  Use the same jargon and identifiers as the landed code. Be detailed and
  complete enough that an agent can implement or verify the contract without
  reconstructing missing decisions. Agent-facing does not mean opaque prose.

Human-facing README pages and notebook Markdown must not display raw checksum
values or explain hash bookkeeping. Give the verification command, expected
success and recovery action instead. Keep exact digests and identity details in
the owning agent-facing technical reference or machine-readable manifest; link
to that owner when needed. Preserve the actual checks and frozen evidence.

Tutorial notebooks (`.ipynb`) remain learner-facing. A Markdown filename
containing `tutorial` does not change its audience. Runtime prompt, skill and
advice Markdown also carries executable input meaning: changing its wording
requires the corresponding behavior and identity review, not only a prose review.

Keep navigation hierarchical: a repository README introduces its major areas;
each area's README introduces the next level and links to the owning technical
reference. Keep detailed contracts in non-README documents. Do not duplicate a
rule in several indexes or make a parent README enumerate every leaf document.

Every new or modified human-facing page must receive a readability and logic
review using the non-dialect parts of the
[DongbeiGPT skillset](https://github.com/yuema137/DongbeiGPT):
`clear-tech-explainer` for causal structure, `concrete-example` when a worked
trace helps, and `plain-chinese` for Chinese prose. Apply the clarity principles
to English pages without translating them or adding regional voice. Check
whether a new reader can identify what to do, in what order, which file owns
each choice, and how to recognize success. Simplification must preserve
technical conditions and distinctions.

For both audiences, compare behavior claims and commands against the exact
source revision and relevant tests: paths, flags, defaults, units, shapes,
parameter interactions, outputs and failure cases. Distinguish source review
from commands actually executed. Plans establish intended work; verify current behavior from source and tests.
Keep development chronology, incident narratives and status ledgers out of
contributor rules. Link to the owning contract instead of duplicating rules in README
files; keep each rule authoritative in one place.

Apply this review whenever a page is created or changed; this does not require
an unrelated repository-wide rewrite. Explicitly requested human reading
mirrors remain reading aids for the authoritative source, not separate rule
owners.

Public installation/download examples and current repository entry links use
`yuema137/SIDERIUS` and `yuema137/siderius-exp`. Development PRs remain in
Galileo-Sandbox. Changing documentation links does not authorize publishing or syncing a
release.

## Development and publication

Develop and review in Galileo-Sandbox. Synchronize to yuema137 only for a
stable release selected by the operator. Release preparation follows the
PR-scope workflow above and does not authorize unrelated changes or publication.
