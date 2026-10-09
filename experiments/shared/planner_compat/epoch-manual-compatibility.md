# Explicit paper epoch manual compatibility

## Scope and ownership

Infra #684 removes four implicit 100-epoch limits. `TrainConfig.epochs` still
defaults to 10; an absent operator cap means no additional clamp. Scientific
paper ceilings belong to the experiment: all eleven units in
`paper-replay-369.json` already declare `--max_epochs 100`,
`--trial_max_epochs 100` and `--formal_max_epochs 100`.

The new `epoch_manual_v9.py` providers compose the v8 runtime, v7 storage and
v6 preflight projections. They accept exactly the frozen `pre_pr` configuration
manual with only `schemas.TrainConfig.properties.epochs.maximum` removed.
They render the existing frozen early/late manual, including its paper-era
maximum of 100. The input is never modified. An extra field, changed default,
changed minimum, reintroduced maximum or old manual refuses; this is not a
general schema-stripping fallback. V4–v8 retain their original qualification
and refuse the new production manual.

| Recorded lineage | New explicit planner strategy |
| --- | --- |
| TESS, LIGO, TIDMAD NoPrior | `legacy-9b78d505cb11-paper-epochs-v9` |
| Project8 dual, TIDMAD analysis-on | `legacy-9b78d505cb11-paper-late-epochs-v9` |

`paper-epoch-caps-v1.json` is a separate migration overlay extending
`../runtime_compat/paper-measured-completion-v1.json`. Apply its common launch
parameters and the matching `covered_units` row to a copied experiment and LLM
configuration. It preserves all eleven recorded run/revision/launch identities,
the selected verifier family and measured admission, adds the explicit three
100-epoch caps, and selects v9. It is not a complete launcher or launch approval.
Historical run IDs in the overlay identify evidence; use a new run ID and output
workspace for execution. Archived task/workflow declarations remain untouched.

## Installation and migration

Use a clean qualified framework checkout at
`fec37b60f5701db8993ac4d29539b2f1090e4c2b`, or a tree-equivalent revision with
the same qualified assemblies. The exp root framework pin remains `769bba`;
that old schema cannot select v9. The root lock changes only the planner and
preflight local package versions, not the framework or other dependencies.

From the selected infra checkout, after its own frozen environment sync, install
the packages from one explicit exp checkout (set `EXP_CHECKOUT` to that path):

```sh
uv sync --group dev --frozen
uv pip install --python .venv/bin/python --no-deps \
  "$EXP_CHECKOUT/experiments/shared/planner_compat" \
  "$EXP_CHECKOUT/experiments/shared/preflight_compat" \
  "$EXP_CHECKOUT/experiments/shared/runtime_compat" \
  "$EXP_CHECKOUT/experiments/shared/prompt_compat"
```

Package versions are planner 0.10.0, preflight 0.2.2, prompt 0.10.1 and unchanged
runtime 0.1.0. Installation defaults and previous selectors are unchanged.
Select v9 explicitly under `tune.planner_strategy`; retain the relevant prompt-v2
task binding from the [proposer context migration](../prompt_compat/proposer-budget-v2.md).

Use a new workspace. Keep existing workspaces on their original package and
framework revisions. The new preflight qualification changes its source identity
and inherited planner identities; the prompt qualifier changes prompt identities
including older selectors. Do not override stored identities, relabel old
records, or infer that an unchanged selector permits an in-place resume. V9
identity owns its module, inherited v8 identity and frozen manual bytes; expected
old-profile or wrong-assembly identities refuse at provider resolution.

## Qualification and reproducible offline checks

`evidence/epoch-manual-qualification.json` records the exact source closures,
four startup receipts and installed package checks. At the qualified infra head:

- Estimator closure: 78 files; only `models_format_sandbox.py` and
  `hyperparam_tuning.py` differ from qualified `769bba`. Their differences remove
  the epoch maximum and cooperative cap refusal/description. Arithmetic and
  batch search owners are unchanged. The frozen 45 estimates and 32 batch
  decisions pass, as does installed discovery using an actual small CPU probe.
- Rendering closure: 160 files; only `hyperparam_tuning.py` differs from
  qualified `830d819f`. All 47 frozen boundary cases match. The new assembly is
  admitted only to prompt v2, not v1; no new prompt profile family is needed.
- Runtime verifier closure: all 18 files are unchanged from qualified `b13b9263`.
  Runtime package sources, version and qualification are unchanged. The
  separate `training_budget.py` envelope lies outside this closure: its only
  change removes an upper validation bound; explicit values at or below 100
  and budget decision logic remain unchanged. Do not infer that an unchanged
  verifier digest by itself qualifies that separate schema change.

Run focused tests with the selected framework's Python, not exp's older pinned
framework environment:

```sh
.venv/bin/python -m pytest -q \
  "$EXP_CHECKOUT/experiments/shared/planner_compat/tests/test_epoch_manual_v9.py" \
  "$EXP_CHECKOUT/experiments/shared/planner_compat/tests/test_paper_v4.py" \
  "$EXP_CHECKOUT/experiments/shared/planner_compat/tests/test_runtime_verifier_v8.py" \
  "$EXP_CHECKOUT/experiments/shared/preflight_compat/tests/test_historical_estimation.py"
.venv/bin/python "$EXP_CHECKOUT/experiments/shared/preflight_compat/check_installation.py" \
  --infra-checkout "$PWD" --output "$OUTPUT/preflight-installation.json"
.venv/bin/python "$EXP_CHECKOUT/experiments/shared/prompt_compat/check_installation.py" \
  --profile-version 2
```

`test_paper_v4.py` now explicitly tests the frozen previously reviewed input;
`test_epoch_manual_v9.py` owns live production-manual acceptance and old-profile
refusal. This preserves the archived contract without silently expanding it.

For each task, supply its SHA-checked original model to the existing startup
checker. Bind an empty temporary generated library so operator-installed models
cannot enter the check. Set `CASE`, `MODEL_PLUGIN`, `STRATEGY` to the matching
task, archived model path and selector from the table, then run:

```sh
CHECK_WORKSPACE=$(mktemp -d)
SIDERIUS_CHAIN_WORKSPACE="$CHECK_WORKSPACE" \
SIDERIUS_GENERATED_LIBRARY_DIR="$CHECK_WORKSPACE/generated_library" \
SIDERIUS_PLUGIN_DIRS='' \
.venv/bin/python -m siderius_planner_compat.startup_check \
  --case "$CASE" --model-plugin "$MODEL_PLUGIN" --planner-strategy "$STRATEGY"
```

The checker assembles the current production manual and verifies the complete
system/user message hashes against the original captures. TESS, LIGO, Project8
and TIDMAD NoPrior band 0–3 all passed. These are four recovered startup requests,
not eleven startup captures or reconstructed full scientific conversations.
The remaining selected units have explicit cap/profile mapping coverage.

The 47-boundary comparison uses `prompt_compat/compare.py --profile-version 2`
with explicit original reference checkouts as documented by that tool. Installed
checks verify matching source files, normal entrypoint discovery, child estimator
identity and unknown-assembly refusals. The root package lock passes frozen sync.

This qualification covers recorded inputs, rendered bytes and the explicit
100-epoch ceilings. It does not promise identical retry/rejection trajectories
for formerly invalid proposals above 100, full historical conversations, model
responses, scores, GPU measurements or training replay. API/GPU/training calls
for this companion qualification are zero.
