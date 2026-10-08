# Historical prompt compatibility

Use this package when you want current infra to assemble the historical prompt
text for the paper experiments. It contains explicit rendering profiles, frozen
inputs, and offline comparison tools. Infra keeps its current default behavior;
installing this package alone changes nothing.

The checks compare messages and, for one archived failure, the request sequence.
They do not call an LLM, train a model, download data, or reproduce a paper score.
Some intermediate replies were not archived. The [coverage report](parity-report.md)
separates recovered inputs from supplementary branch tests and missing evidence.

## 1. Install into the infra environment

Set `INFRA_CHECKOUT` and `EXP_CHECKOUT` to your own absolute checkout paths.
Use the infra revision recorded in
[qualification.json](src/siderius_prompt_compat/qualification.json); the package
refuses an unqualified rendering assembly. Both repositories need the companion
changes described in the coverage report.

```bash
cd "$INFRA_CHECKOUT"
uv sync --group dev --frozen
uv pip install --python "$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/planner_compat" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat"
```

This installs the package versions declared by the selected exp checkout
(currently planner compatibility 0.8.0 and prompt compatibility 0.8.0) as normal
packages. Do not share another checkout's virtualenv or add its source through
`PYTHONPATH`. Running `uv sync` again can remove these separately installed
consumer packages; reinstall them before using a historical profile.

Version 0.7.0 also supports the renderer assembly tested at infra
`34660bed0960f3bcad60ba30aaedffaaf617ff8b`. Its
[qualification report](release-renderer-qualification.md) records 47 matching
offline message comparisons and the four paper proposer routes. This is a
development candidate, not a new public installation pin or a completed
onboarding release. Changing the package changes its recorded identity: use
a new workspace and leave historical workspace locks intact. Retain the old
package and infra revision when using an old workspace's recorded identities.

Version 0.8.0 additionally qualifies the declared renderer assembly at infra
`5afbdcb2ed9eab61c99cb14192b116fe1a479a0f`. The
[new source review and receipt](qualifications/portable-ceiling/report.md) record
47 matching frozen message cases, four historical proposer routes and retained
unknown-assembly refusal. Only the portable GPU-ceiling schema declaration
changed inside the rendering closure; runtime resource policies remain outside
this message-parity claim. Root installation pins and historical configurations
are not promoted by this qualification. The same new-workspace identity rule
applies; preserve the old package for old recorded locks.

## 2. Configure copies in a new workspace

Copy the intended experiment's task package and experiment configuration into
your external workspace, preserving relative paths. Keep archived files and old
workspace locks unchanged. There are two separate choices:

The v4 choices below reproduce the archived inputs used by the offline
comparisons. If a new run will produce factual runtime-refusal records, use
the corresponding v5 planner choice from
[the paper runtime overlay](../planner_compat/profiles/paper-runtime-v5.json)
instead; keep the task's `prompt_renderer` unchanged. The
[v5 setup instructions](../planner_compat/README.md#historical-runtime-refusal-wording-v5)
explain which copied configuration to update.

| Experiment | Task manifest: `prompt_renderer` | LLM JSON: `tune.planner_strategy` |
| --- | --- | --- |
| TESS, LIGO | `paper-early-v1` | `legacy-9b78d505cb11-paper-v4` |
| Project8 dual representation | `paper-late-v1` | `legacy-9b78d505cb11-paper-late-v4` |
| TIDMAD NoPrior | `paper-tidmad-noprior-v1` | `legacy-9b78d505cb11-paper-v4` |
| TIDMAD analysis-on at `c0467447` | `paper-analysis-c0467447-v1` | `legacy-9b78d505cb11-paper-late-v4` |

For example, add this top-level field to your **copied LIGO task composition
YAML**, the file passed to `--task_composition`:

```yaml
prompt_renderer: paper-early-v1
```

In your copied LLM JSON, retain the other settings and set
`tune.planner_strategy` to `legacy-9b78d505cb11-paper-v4`. The first setting
selects implementor/proposer/validator/interpreter rendering; the second selects tuner
planner rendering. See [planner setup](../planner_compat/README.md#match-the-papers-actual-planner-startup)
for that separate contract.

For the listed **TIDMAD analysis-on** revision only, also add the following to
the **analysis-policy YAML referenced by the copied task composition**:

```yaml
recovery_policy:
  schema_version: 1
  generated_program_retries: 0
  plan_retries: 1
```

The same object is saved in
[analysis-c0467447-recovery-v1.json](profiles/analysis-c0467447-recovery-v1.json).
A retry here means a fresh attempt after the first draft and its representation
repair both fail. Thus `0` stops generated-program preparation after those two
invalid replies. `1` retains the historical shared plan retry. Omitting this
policy keeps current infra's one additional attempt at both stages.
Validation, access rules and the original deadline still apply.

These settings change run identity. Launch into a **new workspace** using your
experiment's launcher and the copied configuration paths. Do not resume an old
workspace in place. The profiles restore the qualified presentation; they do
not authorize historical data access or disable current execution checks.

## 3. Inspect the offline comparisons

[parity-report.md](parity-report.md) explains what was compared. The committed
JSON receipts in [evidence](evidence/) contain reference revisions, fixture
hashes, provider identities, message hashes, and outcomes.

To regenerate the comparisons, prepare a separate infra checkout and its own
frozen `.venv` for each historical revision listed in the report. Create a
`references.json` file using your local paths:

```json
{
  "tess": "/your/checkouts/tess-reference",
  "ligo": "/your/checkouts/ligo-reference",
  "project8": "/your/checkouts/project8-reference",
  "tidmad": "/your/checkouts/tidmad-reference",
  "analysis": "/your/checkouts/analysis-reference"
}
```

Then run:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/compare.py" \
  --candidate "$INFRA_CHECKOUT" \
  --references /your/references.json \
  --output /your/new-comparison-directory
```

The command launches each checkout's own Python, refuses dirty infra source or
a wrong reference revision, and exits nonzero for errors or differing messages.
`comparison.json` summarizes results. Each case also has `reference/` and
`candidate/` directories containing `system.txt`, `user.txt`, and `receipt.json`.
The frozen fixtures supply all rendering inputs; you do not need the original
datasets or the archive paths retained as provenance in those fixtures.

To check the installed package against this source tree and its historical
source inventory, run `check_installation.py` with the same infra Python. Its
Git object database must contain the historical revisions. It also verifies
that an unqualified assembly is refused.

## 4. Replay the archived failure, when available

This additional check needs the original analysis archive directory containing
`input.json` and `structured_output_receipts.jsonl`. It reads the two saved
invalid replies, validates their hashes, and feeds them through preparation.
It never executes their generated programs.

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/replay_generated_failure.py" \
  --archive "$ARCHIVED_ANALYSIS_DIRECTORY" \
  --receipt-sha256 b60e19459d967a99e5887328c5721d597ab442dc86eb2bdb343d1085bdcb2144 \
  --profile paper-analysis-c0467447-v1 \
  --recovery-policy "$EXP_CHECKOUT/experiments/shared/prompt_compat/profiles/analysis-c0467447-recovery-v1.json" \
  --output /your/new-failure-replay-directory
```

`result.json` records request order, message hashes and termination;
`messages.json` contains the text. The expected historical outcome is
`failed_after_archived_repair` after two requests. Run the original revision
without `--profile` or `--recovery-policy` for the reference. Omit both on the
current revision to observe its preserved default: a third generation request,
where replay stops because no saved reply exists.

## Runtime-feedback candidate qualification

Version 0.2.0 also declares the candidate infra assembly listed under
`additional_assemblies` in `qualification.json`. This covers the added runtime
feedback schema field; unknown assemblies still fail before rendering. The
original qualified assembly remains supported. The package identity changes
because its qualification source changes: use a new workspace and retain
version 0.1.0 with its original exp revision for old workspace locks.

For historical planner input produced by the new factual runtime feedback,
select the explicit [runtime v5 planner provider](../planner_compat/README.md#historical-runtime-refusal-wording-v5)
in addition to the task's prompt profile above. The raw record retains the
new facts. This qualification does not change the repository's published infra
pin or authorize public release.

## Recover formal evidence for an old interpretation cache

Current infra checks the original formal round's Health results before using
its score in a scientific aggregate. Older interpretation caches saved the
score and an authority verdict, but not all of that independent evidence.
Reading an old cache still works; a missing proof is reported as an exclusion.

If you have the original tuner outputs and their effective Health policy, use
`recover_formal_evidence.py` to create a **separate replay input**. It keeps the
old text and numbers and adds evidence recovered from the matching formal
record. It never changes the archive or enables in-place continuation of an
old workspace. Missing, ambiguous or contradictory sources cause an error.

Create `recovery-request.json` in your external project. It names three inputs:

| Field | File to select |
| --- | --- |
| `interpretation` | The archived `interpretation_*.json` containing the cache you want to recover |
| `health_policy` | That run's `health_checks_effective.yaml` |
| `run_outputs` | An array of original `run_output_*.json` files, with one unambiguous producing run for each cached formal score |

Each file is an object with an absolute `path` and its SHA-256 file digest in
`sha256`. Obtain the digest with `sha256sum /your/file`; do not use a digest from
a different copy. For example, the request has this structure (replace every
path and digest before running):

```json
{
  "interpretation": {"path": "/your/archive/interpretation_iter_003.json", "sha256": "<64-character file digest>"},
  "health_policy": {"path": "/your/archive/health_checks_effective.yaml", "sha256": "<64-character file digest>"},
  "run_outputs": [
    {"path": "/your/archive/model_a/run_output_iter_001.json", "sha256": "<64-character file digest>"},
    {"path": "/your/archive/model_b/run_output_iter_002.json", "sha256": "<64-character file digest>"}
  ]
}
```

Select the independent-formal-evidence assembly listed in
`qualification.json`. Earlier entries preserve older renderers but do not
support this cache recovery. Run with that clean infra checkout's own Python:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/recover_formal_evidence.py" \
  --expected-revision "$(git -C "$INFRA_CHECKOUT" rev-parse HEAD)" \
  --request /your/project/recovery-request.json \
  --output /your/project/recovered-cache
```

The output directory must be new. `interpretation.json` is the recovered copy;
`receipt.json` records source digests, the selected formal record identities,
the resolved gate roster, the infra revision and the output digest. The tool
also verifies that each producing run recorded the same effective Health policy
body. Do not replace missing policy evidence by declaring that Health was off.

This is input recovery, not a training command. It calls no provider and trains
no model. Use the recovered cache only through an explicitly configured replay
or new-workspace workflow. The [formal-evidence qualification report](formal-evidence-parity.md)
describes the paper archive coverage and the limits of the prompt comparisons.

## Proposer model selection after the routing fix

The proposer now honors each stage's model selection. Earlier infra releases
used `propose.reasoning` for comparison, reasoning and proposing, even when
the other entries selected different models. To keep an affected experiment's
historical selection, set all three entries in **your external experiment's**
LLM JSON to its old reasoning provider, model, reasoning effort and retry limit.
For a new experiment, select whichever model you intend to use at each stage.

The four paper configurations already select the historical model in all three
entries, so they need no rewrite. Version 0.4.0 qualifies the repaired infra
assembly listed in the package's `qualification.json`. The
[routing audit](proposer-routing-audit.md) records the original evidence and the
limits of that claim.

To check your copy of those four configurations, run this command with the
qualified infra checkout's own environment:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_paper_proposer_routing.py" \
  --expected-revision "$(git -C "$INFRA_CHECKOUT" rev-parse HEAD)" \
  --output /your/project/new-routing-receipt.json
```

The parent directory must exist and the receipt filename must be new. Success
prints four `MATCH` rows and saves the selected routes and input digests. This
command checks model configuration without calling an API or training. Prompt
text is checked separately by the frozen comparison command above. A changed
plugin identity requires a new workspace; do not use this upgrade to resume an
old workspace in place.

By default the checker reads the exp checkout containing the script. To inspect
a separate copy of the repository, add `--exp-checkout /your/exp-copy`.


## Static preflight evidence

Version 0.5.0 qualifies the static-evidence infra assembly in `qualification.json`.
For a new workspace that will generate passing structural-preflight evidence,
select the corresponding explicit
[v6 planner provider](../planner_compat/README.md#passing-static-preflight-evidence-v6).
It keeps the saved record intact and removes only the new qualified fields from
its historical prompt input copy. Installation alone does not select v6.

A static refusal is now described as a static decision, including in repeated
failure summaries. It is not reported as measured GPU excess and cannot justify
an architectural ban. New static refusal records are deliberately rejected by
the historical v6 projection: the package cannot reconstruct a truthful old
presentation for them. The [compatibility report](static-preflight-parity.md)
separates archived-input equality, current producer checks, and execution-policy
limits. Neither package changes the public infra pin or authorizes resuming an
old workspace in place.
