# Historical planner compatibility package

This package preserves the planner strategies removed from SIDERIUS framework
source. Installing it declares an installation default, so an existing caller
that omits a strategy can retain the historical planner prompt behavior.

Offline checks verify that this package preserves the historical planner text
for the covered inputs. Twelve cases cover the current historical prompts,
including the agent-owned Formal training appendix; six cover the older prompts
with an empty loss registry. The [paper verification report](paper-parity.md)
adds LIGO startup and shared-branch comparisons for the four paper tasks. The
[controlled TESS comparison](../../phyts_tess/planner_strategy_comparison_372/report.md)
is complete; it does not claim improved scientific performance.

This package alone does not reproduce a paper result or migrate an existing
workspace. Historical model/history import and non-empty older loss registries
remain unqualified. Follow the workspace rules below rather than resuming an old
run under a guessed strategy.

The historical loss-search and recovery wording is also archived here. Ten
additional offline cases check that moving this helper preserves final prompts
for free loss choices and task-locked builtin/custom objectives. Infra no longer
owns that historical strategy text.

## Install into the environment that will run infra

Use the infra checkout for the paired issue #372 change. A released infra
revision without `agent.planner_strategy` cannot load this package. First
create that checkout's own environment using its installation instructions.
Then install this directory into that environment:

```bash
# Replace both paths with your checkouts; no credentials are needed here.
INFRA_CHECKOUT=/absolute/path/to/SIDERIUS
EXP_CHECKOUT=/absolute/path/to/siderius-exp
uv pip install --python "$INFRA_CHECKOUT/.venv/bin/python" --no-deps \
  "$EXP_CHECKOUT/experiments/shared/planner_compat"
```

Use a normal installation for a run whose identity must remain fixed. Do not
edit the package during execution. Both repositories' public download locations
are [yuema137/SIDERIUS](https://github.com/yuema137/SIDERIUS) and
[yuema137/siderius-exp](https://github.com/yuema137/siderius-exp); the paired
change must be merged and synchronized before those paths include this API.

Inspect the selected identity without calling an LLM:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" -c \
  'from agent.planner_strategy import resolve_planner_strategy; print(resolve_planner_strategy(None).identity.model_dump_json(indent=2))'
```

The declared default is `legacy-9b78d505cb11-v1`. A missing package or multiple
installed defaults produces an explicit error. Infra never guesses which
historical experiment you intended.

## Select a strategy for a new experiment

In your workspace's LLM configuration, add the selector to the existing `tune`
object and keep its planner/reflector model settings:

```json
{
  "tune": {
    "planner_strategy": "legacy-9b78d505cb11-v1",
    "planner": {"provider": "openai", "model_id": "YOUR_MODEL_ID"},
    "reflector": {"provider": "openai", "model_id": "YOUR_MODEL_ID"}
  }
}
```

Run your existing experiment script with this LLM configuration. The standalone
infra tuner also accepts `--planner_strategy legacy-9b78d505cb11-v1`.
An explicit choice overrides the installation default. `native-timing-v1`
selects the new timing-aware planner and changes the treatment; it is not the
historical fallback.

The additional `legacy-691617f04b42-v1` source variant is preserved for the older
Majorana/SuperNEMO records. Six synthetic cases match its original assembled
prompts, but the historical runs themselves are not yet qualified. Its API adapter currently
supports an absent or verified-empty custom-loss inventory only; non-empty or
unavailable inventory information refuses explicitly. It also refuses new
agent-owned Formal training and independent epoch-validation scopes, which
were absent from its original planning path. No loss information is silently
dropped to make the old call signature work. Do not substitute it into a
historical run and report successful replay.

## Keep old results intact

### Historical prompts with the ordering provenance repair (#447)

Use `legacy-9b78d505cb11-ordering-v2` explicitly when a new run on repaired infra
must retain the pre-#447 planner history format. Change only `tune.planner_strategy`
in the LLM configuration shown above, or pass
`--planner_strategy legacy-9b78d505cb11-ordering-v2` to the standalone tuner.
The installation default remains `legacy-9b78d505cb11-v1`; upgrading this package
does not switch an existing experiment to v2.

The repair records whether ordering was selected and which phase refused an
attempt. For example, a new record may say "sequential order selected; training
admission refused." That evidence remains in the saved record. Before rendering
the historical planner prompt, v2 makes a separate copy in the old format: this
kind of refusal had no ordering fields before #447, so those fields are omitted
from that copy. A successful record keeps its original ordering fields. Records
without the new observation pass through unchanged.

Install package version 0.2.0 or later into an infra checkout containing the
paired [infra PR #599](https://github.com/Galileo-Sandbox/SIDERIUS/pull/599),
using the installation command above. Then check the installed pair offline:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" -m siderius_planner_compat.ordering_check
```

Success reports 15 producer cases, 17 matching final prompt pairs, and zero API
calls. This check needs no dataset or GPU. It tests raw saved history records;
reconstructed records with newly filled defaults are not a qualified substitute.
Contradictory observations raise an error instead of silently discarding evidence.

The new plugin has a different identity. Start in a **new workspace** and retain
a migration record linking to the old evidence; do not change an old workspace's
lock. This package does not import models or history for you. The
[ordering compatibility report](ordering-parity.md) states the verified scope
and explains why exact prompt text does not promise identical stochastic results.

Do not edit an old `run_invariants_lock.json` to make a new run start. A lock
without a strategy identity cannot prove which installed plugin it used. The
new framework refuses that resume rather than filling in a guess.

Keep the original workspace and receipts. A verified migration must create a
new workspace, bind the historical provider explicitly, and retain a separate
record linking to the old evidence. The migration procedure is not automated
by this package yet. If provenance cannot be verified, use the old infra
revision for that run. SuperNEMO's missing workspace is an acknowledged exception;
it will be rerun separately and is not part of the paper models.

Scientific experiments are checked individually before migration. Internal
framework tests keep their original code revision and records; this work does
not adapt those old tests to new plugins. The [migration contract](migration.md)
lists the evidence required before a scientific migration can be called verified.

`source_manifest.json` records the original prompt source revisions and hashes.
The archived modules remain byte-identical to those sources. Preserving source,
matching final prompts, replaying archived responses, and obtaining the same
score from a fresh stochastic run are different checks; only report the checks
actually completed.

## Check the installed package without an API call

From the same infra environment used above:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" -m siderius_planner_compat.self_check
```

Success reports 12 current, six early and ten composed-loss matching prompt pairs,
two early empty-registry
boundary cases, and refusal of uncertain registry information before any provider
call. The recorded reference digests came from the original infra checkout,
not from the new renderer. All clients are blocked from network access. These
checks use synthetic inputs; the early comparisons cover an empty registry only
and do not establish scientific replay.

## Correct new runs or inspect historical prompts (#369)

New infra records the actual trial/formal role even when an attempt is skipped
or fails. Use that corrected behavior for ordinary runs. Do not change a trial
back to formal to reproduce a known recording bug.

For an explicitly requested historical **planner text** comparison, package
0.3.0 provides `legacy-9b78d505cb11-attempt-role-v3`. Copy the experiment's
`agents.json` into your new workspace and set its `tune.planner_strategy` to
that selector. Pass your copied file through `--llm_config`. This is opt-in:
it changes neither the installed default nor old provider identities. The
adapter changes only a copy of raw history presented to the historical planner;
the saved records retain their correct roles. Choose `native-timing-v1` when you
want the framework's current planner strategy instead of historical policy.

After installing this package into the qualified infra environment using the
installation instructions above, check the pair without credentials or a GPU:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" -m siderius_planner_compat.attempt_role_check
```

Success reports 15 producer cases, 30 identical final system/user prompt pairs,
and zero API calls. This is an offline controlled boundary check, not a promise
of identical new LLM responses, scientific trajectories or final artifacts.

[paper-replay-369.json](paper-replay-369.json) records the audited launch parameters
and source revisions for the 11 native paper workflow units, including TIDMAD's
bands. It is an evidence inventory, not a file to pass directly to the launcher.
Use its `launch_parameters` with the referenced experiment, remap data/config
paths to your machine, and use a new workspace. Both validation limits are
`null` (disabled); omit their CLI flags, rather than passing the string `null`.
The dataset/split definitions, models and agent settings remain owned by the
referenced experiment revisions. This inventory does not replace those assets
or provide an automatic historical-workspace import.

Archived TESS has 28 skipped trial records labeled formal; Project8 has one.
Their saved per-attempt configurations identify the actual trial role. The
archives remain unchanged. These skips produced no successful score, but their
history may have influenced later planning. LIGO and the eight audited TIDMAD
workflow units had no such mismatch in the inspected run-output records. This
is a bounded archive audit, not proof that every attempted iteration survived.

TIDMAD analysis-on used generated external composition files. The historical
composition and analysis-policy bytes have now been reconstructed for all four
bands and verified against the launch-receipt hashes. See the
[startup compatibility report](paper-startup-parity.md#tidmad-analysis-input-recovery)
for their locations and how to regenerate them with local paths. The
[role compatibility report](attempt-role-parity.md) describes the narrower v3
record-conversion boundary.

## Match the paper's actual planner startup

For paper-era planner text, install package **0.4.0** into an infra version that
supports `PlannerStrategy.config_manual_renderer`. V4 also restores the correct
configuration manual, which v3 does not change. Select the profile in your copied
LLM configuration's `tune.planner_strategy`:

| Experiment | Selector |
| --- | --- |
| TESS, LIGO, TIDMAD NoPrior | `legacy-9b78d505cb11-paper-v4` |
| Project8 dual, TIDMAD analysis-on | `legacy-9b78d505cb11-paper-late-v4` |

For example, LIGO's historical manual predates three training options. Its v4
profile renders that manual for the planner while the current executor keeps
its validated schema. Project8 already had those options, so its profile keeps
them. Unknown manual changes stop with an explicit qualification error. Neither
profile becomes an installation default. Start in a new workspace.

Four checks use each task's actual archived model, task text, model description
and advice. Supply the archived first model file, not a newly generated file
with the same name; its SHA-256 must match the frozen reference:

```bash
MODEL_PLUGIN=/absolute/path/to/archived/dual_domain_chirp_fuser.py
"$INFRA_CHECKOUT/.venv/bin/python" -m siderius_planner_compat.startup_check \
  --case ligo --model-plugin "$MODEL_PLUGIN"
```

Repeat with `--case tess`, `project8` or `tidmad` and the corresponding archived
model listed in the [verification report](paper-startup-parity.md). Success
prints the matching system/user hashes and `api_calls: 0`. These checks need no
dataset, API key or GPU. They render the current manual through the installed
historical profile, rather than bypassing production manual assembly.

To recapture the startup through the tuner itself, `capture_startup.py` accepts
`--input /path/to/startup-spec.json --output /path/to/new-capture`. Unlike the
frozen check, this requires the declared task package and local dataset metadata.
The input declares `composition`, `composition_fingerprint`, `seed_plugin_path`,
`seed_plugin_sha256`, `model_description_path`, `model_description_sha256`,
`data_dir`, and `tuner_parameters` (validated `HyperparamTuningInput` fields).
The output directory contains `tuner_input.json`, `planner_arguments.json`,
`messages.json`, and `receipt.json`, plus startup bookkeeping. The first planner
message ends the capture; no model response or training follows.

This verifies planner startup, supplemented by the existing later-round branch
and history-format checks. Full interpret/propose/implement/analyze/reflect
conversation replay is a separate follow-up; these checks do not claim it.

## Historical runtime-refusal wording (v5)

New infra runtime-refusal feedback distinguishes insufficient timing evidence
from a measured budget excess. New experiments should retain those facts.
For an explicit historical paper replay, the following providers restore the
old refusal wording in the planner input only:

- `legacy-9b78d505cb11-paper-runtime-v5`: the early paper configuration manual.
- `legacy-9b78d505cb11-paper-late-runtime-v5`: the later paper configuration manual.

These compose the existing v4 manual and v3/v2 record views. Set the chosen name
as `tune.planner_strategy` in your **external project's** LLM configuration,
and install this package in both the exp and selected infra environments using
the installation procedure above. Preflight must resolve the same provider
identity in both environments. Existing defaults and v1–v4 providers are
unchanged; v5 is never selected automatically.

Only records explicitly marked `memory.runtime_feedback_version="facts-v1"`
and identified as in-subprocess runtime refusals are converted. Unknown
versions or inconsistent admission/status fields fail visibly. Saved records
retain the corrected facts, and historical records without the marker remain
unchanged. This preserves presentation for supplied history; it does not
restore incorrect execution decisions or promise identical new training runs.

Select a new workspace when changing providers. Do not rewrite an old lock or
resume an old workspace under the new identity. The repository's default infra
pin remains the published qualified revision; candidate-infra checks use a
separate explicit checkout until its release is selected. This package update
does not publish or select a new infra revision.

The exact per-task configuration overlays are saved in
[paper-runtime-v5.json](profiles/paper-runtime-v5.json), including the separate
TIDMAD NoPrior and analysis-on variants. Start from the verified archived
experiment in a **new** workspace. Merge `task_composition_overlay` into its
copied task YAML and `llm_config_overlay` into its copied LLM JSON, retaining
the model, provider, budgets and other settings. Do not replace the entire
`tune` object with the small overlay. For the analysis-on variant only, merge
`analysis_policy_overlay` into the analysis-policy file referenced by that
task. These overlays select presentation/retry compatibility; they do not
import an archived workspace or reconstruct missing artifacts.

To check the explicit new planner selection against a captured paper startup:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" -m siderius_planner_compat.startup_check \
  --case ligo --model-plugin "$MODEL_PLUGIN" \
  --planner-strategy legacy-9b78d505cb11-paper-runtime-v5
```

Use the matching `cases` entry for TESS, Project8 or TIDMAD. The check compares
the resulting system/user hashes with the original capture and makes no API
request. The `tidmad-analysis` entry has separate rendering and archived retry
checks; it is not a fifth `startup_check --case` value.

## Passing static-preflight evidence (v6)

The paired infra #615 change records why its resource estimate accepted a
batch. This adds two fields to experiment history. They are useful for new
experiments, but displaying them would change a historical planner prompt.
Version 0.6.0 adds an explicit historical view that removes those two fields
from a temporary copy before rendering the prompt. The saved record keeps the
evidence, its original numbers, and its training or scoring result.

Use the matching provider in `tune.planner_strategy` in your external project's
LLM JSON:

| Historical configuration | Provider |
| --- | --- |
| TESS, LIGO, TIDMAD NoPrior | `legacy-9b78d505cb11-paper-preflight-v6` |
| Project8, TIDMAD analysis-on | `legacy-9b78d505cb11-paper-late-preflight-v6` |

Retain the other settings and compatibility overlays described for v5 above.
Install this package normally in both environments with the installation
command above, and use a **new workspace**. A v6 provider has a different
identity; it cannot be substituted into an existing workspace lock. Installing
0.6.0 does not select v6 automatically or change existing experiment files.
The infra environment must include the paired #615 evidence schema; this
package does not change the repository's published infra pin.

For example, preflight may accept a batch and training may subsequently fail.
V6 removes only `memory.static_preflight_evidence` and
`memory.preflight_outcome` after validating that the preflight passed. The
training failure remains in the prompt. Records predating these fields pass
through unchanged. An unknown evidence version, an incomplete pair of fields,
or a static refusal stops historical rendering with an error before an LLM
request. V6 cannot truthfully reconstruct the old, potentially misleading
refusal explanation from a new refusal.

The [compatibility contract and archive audit](static-preflight-compatibility.md)
describe the covered records and the limits of this check. The check concerns
prompt inputs; it does not promise identical future LLM responses or retraining
results, and it does not fix the estimator's remaining conservative refusals.

## Scoped storage evidence (v7)

Use package 0.7.0 with the [#419 infra repair](https://github.com/Galileo-Sandbox/SIDERIUS/pull/617)
when a new historical-reproduction workspace needs the old planner view of
storage evidence. Infra now records whether its process counter actually
covers the setup reads. For example, zero reads reported by the calling
process no longer mean warm cache when another service performed the reads.
Those corrected facts remain in the saved record.

After the normal installation above, select one of these values in your
external project's `tune.planner_strategy`:

| Historical configuration | Provider |
| --- | --- |
| TESS, LIGO, TIDMAD NoPrior | `legacy-9b78d505cb11-paper-storage-v7` |
| Project8, TIDMAD analysis-on | `legacy-9b78d505cb11-paper-late-storage-v7` |

Keep the other experiment settings and compatibility overlays. Start a **new
workspace**: v7 has a new identity, and installation does not select it for you.
Before an LLM call, v7 makes a temporary copy of each recent record, validates
the storage evidence, and reconstructs the historical cache label and field
layout from the preserved counter and byte values. It also includes v6's
passing-preflight handling. Invalid or unfamiliar evidence stops rendering
with an error; the saved record is never rewritten.

Run the offline pairing check with the selected infra environment:

```bash
"$INFRA_CHECKOUT/.venv/bin/python" -m pytest \
  "$EXP_CHECKOUT/experiments/shared/planner_compat/tests/test_storage_provenance_v7.py" -q
```

Success reports 42 passing checks without API calls, GPU work, or training.
This covers complete planner request comparisons for the archived four-task
record shapes and controlled counter cases. It does not promise identical
future LLM responses or scientific results. Use the paired #419 infra revision: the package refuses an
unqualified storage producer, and the published exp pin skips these new-producer
cases. The
[storage compatibility contract](storage-provenance-compatibility.md) lists
qualified sources, failure conditions and the narrower analysis-on evidence.
