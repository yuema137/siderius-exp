# Proposer budget-context qualification

## Source pair and bounded claim

Framework baseline: `c7996a352d064229725ab1ebe886b9006bdbf36d`.
Framework candidate: `830d819f3233cad23ac613c1ba1c50f82b8efa88`.
Experiment implementation base: `ebe369aedde246bc9dec3434f53aeb8a8da7e48f`;
the reviewed working-tree package is identified by the exact source closure in
the installation receipts. `siderius-prompt-compat` version: `0.10.0`.

This qualification covers frozen historical rendering boundaries and synthetic
proposer branch requests. It does not reconstruct missing intermediate paper
conversations or reproduce model artifacts/scores. No API, training, inference,
GPU or scientific-data operation was performed.

## Executed results

| Check | Result | Receipt |
| --- | --- | --- |
| Original frozen corpus, baseline v1 | 47/47 MATCH | [Baseline rendering](baseline-rendering.json) |
| Original frozen corpus, candidate v2 | 47/47 MATCH | [Candidate rendering](candidate-rendering.json) |
| Full synthetic request sequences across four task-to-profile mappings | 48/48 MATCH, 156 full requests | [Request comparison](full-request-comparison.json) |
| Baseline installed package, source inventory, refusal | 15 installed files, 11 frozen source entries, four v1 entry points and four unknown-assembly refusals | [Baseline installation](baseline-installation.json) |
| Candidate installed package, source inventory, refusal | 15 installed files, 11 frozen source entries, four v2 entry points and four unknown-assembly refusals | [Candidate installation](candidate-installation.json) |
| Focused package/comparator tests | Six passed | Command below |
| Changed Python lint/format and `git diff --check` | Passed | Commands below |

The full-request witness corpus is one synthetic classification-shaped input,
selected under TESS/LIGO early, Project8 late and TIDMAD NoPrior profile mappings.
Each mapping exercises twelve cases, including both initial pipeline modes,
legacy reasoning/commit, missing budgets, four genuine retry/correction triggers,
text stages and clamped prior output. The native node produces the requests;
only provider replies are scripted. Expected request labels prove each branch
was reached before full system/user string comparison. Data and generated-model
libraries are absent, with the latter bound to isolated temporary workspaces.

The original corpus remains the existing four-task and analysis-on qualification
at its declared boundaries. Its 24 proposer cases compare system templates only;
the supplementary witnesses supply user-request/retry coverage without claiming
those synthetic conversations were historical paper requests.

## Baseline qualification gap

Before this work, v1's accepted assembly list stopped before optional task-owned
model-probe transport reached the selected pre-fix framework. The
[source review](source-review.json) records the changed closure files: optional
fields remain absent for the preserved inputs, and changed implementor/validator
execution branches do not alter the selected pure renderers. No proposer or
proposal-template source changed in this baseline delta.

That source audit was followed by all 47 original comparisons on the exact
baseline. The single additional v1 assembly entry records this independently
qualified comparator. It does not admit the new candidate assembly. Package
tests prove that candidate-v2 qualification cannot silently select v1 behavior.

## Reproduction and provenance

Every framework checkout was synchronized with `uv sync --group dev --frozen`
and executed using its own `.venv/bin/python`. Both baseline and candidate
installed the actual standalone package normally through `uv pip install`;
installation checks compared packaged source/data files and actual entry points.
No source injection or borrowed environment was used. The exp root dependency
pin and lock remain unchanged.

Follow [the migration and offline commands](../../proposer-budget-v2.md), using
fresh output directories. Run the original corpus with `compare.py` once for
each baseline/candidate, selecting `--profile-version 1` / `2` respectively.
Run `check_installation.py --profile-version 1` in baseline and `--profile-version 2`
in candidate. The request comparer checks the baseline against the fixture's
exact source revision; both captures reject dirty framework source.

From the exp checkout, after installing this standalone package into its own
frozen environment, the focused tests are:

```bash
.venv/bin/python -m pytest \
  experiments/shared/prompt_compat/tests/test_budget_profiles.py \
  experiments/shared/prompt_compat/tests/test_compare.py \
  experiments/shared/prompt_compat/tests/test_compare_proposer_requests.py -q
```

Ruff `check` and `format --check` cover the changed provider, both comparison
tools, request capture, installation checker and new test files. Exact message
and fixture hash closures are recorded in the compact JSON receipts; raw
messages remain reproducible output, not a newly claimed historical archive.

V2's qualifier pins the candidate rendering assembly. A later merge with the
same rendering assembly has the same accepted source boundary. Changed package
identities require a new workspace; retain the old installed package and source
bindings when resuming an old workspace. Other historical surfaces and all
limitations in the existing parity report remain outside this claim.
