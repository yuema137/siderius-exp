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

This installs planner compatibility 0.5.0 and prompt compatibility 0.2.0 as normal
packages. Do not share another checkout's virtualenv or add its source through
`PYTHONPATH`. Running `uv sync` again can remove these separately installed
consumer packages; reinstall them before using a historical profile.

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
